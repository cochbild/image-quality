import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container, Grid, Typography, Card, CardContent, Box,
  Chip, Alert, CircularProgress,
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import { getAssessment, type Assessment } from '../api/assessments';

const CATEGORY_LABELS: Record<string, string> = {
  anatomical: 'Anatomical Integrity',
  compositional: 'Compositional Coherence',
  physics: 'Physics & Lighting',
  texture: 'Texture & Surface Quality',
  technical: 'Technical Quality',
  semantic: 'Semantic Integrity',
};

export default function ImageDetail() {
  const { id } = useParams<{ id: string }>();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const parsedId = Number(id);
    if (!Number.isFinite(parsedId) || parsedId <= 0) {
      setError(`Invalid assessment id: ${id}`);
      setLoading(false);
      return;
    }
    getAssessment(parsedId)
      .then(setAssessment)
      .catch((err) => {
        console.error('Assessment load failed', err);
        setError('Failed to load assessment');
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <Container sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error || !assessment) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error || 'Assessment not found'}</Alert>
      </Container>
    );
  }

  const scoreColor = (score: number) =>
    score >= 7 ? 'success' : score >= 4 ? 'warning' : 'error';

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Alert
        severity={assessment.passed ? 'success' : 'error'}
        sx={{ mb: 3 }}
      >
        <Typography variant="h6">
          {assessment.filename} — {assessment.passed ? 'PASSED' : 'FAILED'}
        </Typography>
        {assessment.destination_path && (
          <Typography variant="body2">Moved to: {assessment.destination_path}</Typography>
        )}
      </Alert>

      <Grid container spacing={3}>
        {/* Image */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <Box
              component="img"
              src={`/api/v1/images/${assessment.id}`}
              alt={assessment.filename}
              sx={{ width: '100%', display: 'block' }}
              onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          </Card>
        </Grid>

        {/* Scores */}
        <Grid size={{ xs: 12, md: 6 }}>
          {assessment.category_scores.map((cs) => (
            <Card key={cs.category} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6">
                    {CATEGORY_LABELS[cs.category] || cs.category}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {cs.was_deep_dive && (
                      <Chip
                        icon={<ZoomInIcon />}
                        label="Deep Dive"
                        size="small"
                        color="info"
                      />
                    )}
                    <Chip
                      label={cs.score}
                      color={scoreColor(cs.score) as 'success' | 'warning' | 'error'}
                      sx={{ fontSize: '1.2rem', fontWeight: 'bold', minWidth: 48 }}
                    />
                  </Box>
                </Box>
                {cs.reasoning && (
                  <Typography variant="body2" color="text.secondary">
                    {cs.reasoning}
                  </Typography>
                )}
              </CardContent>
            </Card>
          ))}
        </Grid>
      </Grid>
    </Container>
  );
}
