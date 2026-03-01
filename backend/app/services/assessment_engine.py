import json
import re
from typing import Optional
from app.services.lm_studio_client import LMStudioClient
from app.services.rubric import (
    TRIAGE_PROMPT, DEEP_DIVE_PROMPTS, CATEGORIES,
    DEFAULT_THRESHOLDS, BORDERLINE_LOW, BORDERLINE_HIGH,
)
from app.core.logging import get_logger

logger = get_logger("assessment")


def parse_json_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


class AssessmentEngine:
    def __init__(self, lm_client: Optional[LMStudioClient] = None):
        self.lm_client = lm_client or LMStudioClient()

    async def assess_image(
        self,
        image_path: str,
        thresholds: Optional[dict[str, int]] = None,
        borderline_low: int = BORDERLINE_LOW,
        borderline_high: int = BORDERLINE_HIGH,
        model: Optional[str] = None,
    ) -> dict:
        """Run hybrid triage assessment on a single image.

        Returns:
            {
                "passed": bool,
                "categories": {
                    "anatomical": {"score": int, "reasoning": str, "was_deep_dive": bool},
                    ...
                }
            }
        """
        thresholds = thresholds or DEFAULT_THRESHOLDS

        # Phase 1: Triage pass
        logger.info(f"Triage pass: {image_path}")
        triage_response = await self.lm_client.analyze_image(image_path, TRIAGE_PROMPT, model=model)
        triage_result = parse_json_response(triage_response)

        categories = {}
        for cat in CATEGORIES:
            cat_data = triage_result.get(cat, {})
            score = int(cat_data.get("score", 1))
            reasoning = cat_data.get("reasoning", "")
            categories[cat] = {"score": score, "reasoning": reasoning, "was_deep_dive": False}

        # Phase 2: Deep dive on borderline categories
        borderline_cats = [
            cat for cat, data in categories.items()
            if borderline_low <= data["score"] <= borderline_high
        ]

        if borderline_cats:
            logger.info(f"Deep dive on borderline categories: {borderline_cats}")
            for cat in borderline_cats:
                prompt = DEEP_DIVE_PROMPTS[cat]
                deep_response = await self.lm_client.analyze_image(image_path, prompt, model=model)
                deep_result = parse_json_response(deep_response)
                categories[cat] = {
                    "score": int(deep_result.get("score", categories[cat]["score"])),
                    "reasoning": deep_result.get("reasoning", categories[cat]["reasoning"]),
                    "was_deep_dive": True,
                }

        # Determine pass/fail
        passed = all(
            categories[cat]["score"] >= thresholds.get(cat, DEFAULT_THRESHOLDS[cat])
            for cat in CATEGORIES
        )

        return {"passed": passed, "categories": categories}
