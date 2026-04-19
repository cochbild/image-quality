import { Chip } from '@mui/material';

// Abbreviations are explicit so future category names can't collide
// (e.g. a "texture" vs hypothetical "technician" would both slice to "Tex/Tec").
const CATEGORY_ABBR: Record<string, string> = {
  anatomical: 'Anat',
  compositional: 'Comp',
  physics: 'Phys',
  texture: 'Tex',
  technical: 'Tech',
  semantic: 'Sem',
};

interface ScoreChipProps {
  category: string;
  score: number;
}

export default function ScoreChip({ category, score }: ScoreChipProps) {
  const color = score >= 7 ? 'success' : score >= 4 ? 'warning' : 'error';
  const abbr = CATEGORY_ABBR[category] ?? category.slice(0, 4);
  return <Chip label={`${abbr}: ${score}`} color={color} size="small" sx={{ mr: 0.5 }} />;
}
