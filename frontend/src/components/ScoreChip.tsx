import { Chip } from '@mui/material';

interface ScoreChipProps {
  category: string;
  score: number;
}

export default function ScoreChip({ category, score }: ScoreChipProps) {
  const color = score >= 7 ? 'success' : score >= 4 ? 'warning' : 'error';
  const label = `${category.charAt(0).toUpperCase() + category.slice(1, 4)}: ${score}`;
  return <Chip label={label} color={color} size="small" sx={{ mr: 0.5 }} />;
}
