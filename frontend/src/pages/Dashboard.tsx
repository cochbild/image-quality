import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container, Grid, Card, CardContent, Typography, Button, Box,
  CircularProgress, Alert,
} from '@mui/material';
import { getStats, type Stats } from '../api/assessments';
import { getScans, type Scan } from '../api/scans';
import ScanTable from '../components/ScanTable';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, scansData] = await Promise.all([
          getStats(),
          getScans(10),
        ]);
        setStats(statsData);
        setScans(scansData);
      } catch (err) {
        console.error('Dashboard load failed', err);
        setError('Failed to load dashboard data. Is the backend running?');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <Container sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="warning">{error}</Alert>
      </Container>
    );
  }

  const statCards = [
    { label: 'Total Assessed', value: stats?.total_assessed ?? 0 },
    { label: 'Pass Rate', value: `${stats?.pass_rate ?? 0}%` },
    { label: 'Passed', value: stats?.passed ?? 0 },
    { label: 'Failed', value: stats?.failed ?? 0 },
  ];

  return (
    <Container sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Dashboard</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="contained" onClick={() => navigate('/scan')}>New Scan</Button>
          <Button variant="outlined" onClick={() => navigate('/settings')}>Settings</Button>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((card) => (
          <Grid key={card.label} size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography color="text.secondary" gutterBottom>{card.label}</Typography>
                <Typography variant="h4">{card.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h6" sx={{ mb: 2 }}>Recent Scans</Typography>
      {scans.length === 0 ? (
        <Alert severity="info">No scans yet. Start your first scan!</Alert>
      ) : (
        <ScanTable scans={scans} />
      )}
    </Container>
  );
}
