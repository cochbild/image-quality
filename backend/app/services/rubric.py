CATEGORIES = ["anatomical", "compositional", "physics", "texture", "technical", "semantic"]

DEFAULT_THRESHOLDS = {
    "anatomical": 7,
    "compositional": 6,
    "physics": 6,
    "texture": 5,
    "technical": 5,
    "semantic": 6,
}

BORDERLINE_LOW = 4
BORDERLINE_HIGH = 8

TRIAGE_PROMPT = """You are an expert image quality assessor specializing in AI-generated (text-to-image) artwork. Analyze this image for common t2i defects.

Score each category from 1 (worst) to 10 (best). Be strict and precise.

Categories:
1. ANATOMICAL - Human body accuracy: correct finger count (5 per hand), face symmetry, proper limb count, no merged bodies, correct joint articulation, proper feet/toes
2. COMPOSITIONAL - Scene structure: object scale consistency, perspective coherence, no floating objects, no object merging/fusion
3. PHYSICS - Physical plausibility: shadow direction consistency, shadow presence, reflection accuracy, depth-of-field consistency, gravity logic
4. TEXTURE - Surface quality: skin realism (not waxy/plastic), hair quality, fabric integrity, material consistency, no edge bleeding
5. TECHNICAL - Rendering quality: no noise artifacts, no color banding, consistent resolution, no tiling/repeating patterns, clean edges
6. SEMANTIC - Logical consistency: text readability (if present), correct object counts, contextually appropriate combinations, logical spatial relationships

If NO humans are present in the image, score ANATOMICAL as 10.

Respond ONLY with valid JSON in this exact format, no other text:
{
  "anatomical": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "compositional": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "physics": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "texture": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "technical": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "semantic": {"score": <1-10>, "reasoning": "<brief explanation>"}
}"""

DEEP_DIVE_PROMPTS = {
    "anatomical": """You are an expert anatomist reviewing an AI-generated image for human body defects. Examine EVERY detail carefully.

Check systematically:
HANDS: Count fingers on each visible hand. Are there exactly 5? Check thumb placement (correct side?). Check finger proportions, joint bending direction, nail placement. Are any fingers fused or merged?
FACE: Are eyes symmetric and at the same height? Correct pupil shapes? Mouth/teeth intact? Ears present and correctly placed? Nose bridge intact? Skin texture natural (not waxy)?
BODY: Count all limbs. Are any bodies merged together? Do all joints bend in anatomically possible directions? Are proportions correct (head-to-body ratio, arm length vs torso, etc.)?
FEET: If visible, correct toe count? No fused feet? Proper orientation?

If NO humans are present, score 10.

Score 1-10 where:
- 10: Flawless anatomy
- 7-9: Minor imperfections (slight asymmetry, minor proportion issues)
- 4-6: Noticeable defects (extra/missing finger, mild face distortion)
- 1-3: Severe deformations (merged bodies, extra limbs, melted features)

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "compositional": """You are an expert compositor reviewing an AI-generated image for structural defects.

Check systematically:
SCALE: Are all objects at correct relative sizes? No impossible scale relationships?
PERSPECTIVE: Is there a consistent vanishing point? Do lines converge correctly?
SPATIAL: Are objects properly grounded? Anything floating without support? Any objects impossibly merged or overlapping?
FOREGROUND/BACKGROUND: Consistent relationship? No jarring transitions?

Score 1-10 where:
- 10: Flawless composition
- 7-9: Minor inconsistencies
- 4-6: Noticeable errors (wrong scale, perspective breaks)
- 1-3: Major structural failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "physics": """You are a physics expert reviewing an AI-generated image for physical plausibility.

Check systematically:
SHADOWS: Do all shadows point in a consistent direction? Does every grounded object cast a shadow? Are shadow lengths proportional?
REFLECTIONS: Are reflections in mirrors/water/glass accurate? Do they match the objects they reflect?
LIGHTING: Is the light source consistent? Do highlights and shadows agree on light direction?
DEPTH OF FIELD: Is blur consistent with a single focal plane? No randomly sharp/blurry regions?
GRAVITY: Are structures properly supported? Do liquids behave correctly?

Score 1-10 where:
- 10: Physically plausible scene
- 7-9: Minor inconsistencies
- 4-6: Noticeable violations (wrong shadow direction, missing reflections)
- 1-3: Major physics failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "texture": """You are a texture and materials expert reviewing an AI-generated image for surface quality.

Check systematically:
SKIN: Does skin look natural? Has pores, fine wrinkles, subtle color variation? Or is it waxy, plastic, overly smooth?
HAIR: Natural variation in strands? Proper physics? Not merging with background? Natural hairline?
FABRIC: Correct fold patterns? No impossible pattern warping? Functional clothing design? No texture bleeding?
MATERIALS: Do metals look metallic? Glass translucent? Wood grainy? Consistent material properties across each surface?
EDGES: Clean boundaries between different materials? No color/texture bleeding between objects?

Score 1-10 where:
- 10: Photorealistic textures
- 7-9: Minor quality issues
- 4-6: Noticeable artifacts (waxy skin, uniform hair, pattern warping)
- 1-3: Severe texture failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "technical": """You are a technical image quality expert reviewing an AI-generated image for rendering artifacts.

Check systematically:
NOISE: Any visible noise patches? Residual denoising artifacts? Grain inconsistencies?
BANDING: Color banding in gradients or smooth areas? Visible gradient steps?
RESOLUTION: Consistent sharpness across the image? No regions at different quality levels?
PATTERNS: Any tiling or repeating artifacts? Watermark-like ghost patterns? Grid structures?
EDGES: Clean edges on all objects? No halos, aliasing, or moire patterns? No edge bleeding?

Score 1-10 where:
- 10: Technically flawless
- 7-9: Minor artifacts
- 4-6: Noticeable technical issues (banding, noise patches, resolution inconsistency)
- 1-3: Severe rendering failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "semantic": """You are a semantic consistency expert reviewing an AI-generated image for logical coherence.

Check systematically:
TEXT: If any text is visible, is it readable? Correctly spelled? In the right language? Or garbled/distorted?
COUNTING: Do object counts match what the scene implies? No duplicate objects that shouldn't exist? No missing expected objects?
CONTEXT: Are object combinations contextually appropriate? No anachronisms? No culturally impossible scenarios?
SPATIAL LOGIC: Do spatial relationships make sense? Are objects in expected positions relative to each other?
OBJECT INTEGRITY: Are all objects complete? No hybrid/contradictory states? No missing expected components (e.g., car without wheels)?

Score 1-10 where:
- 10: Semantically flawless
- 7-9: Minor inconsistencies
- 4-6: Noticeable logical errors (garbled text, wrong object count)
- 1-3: Major semantic failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",
}
