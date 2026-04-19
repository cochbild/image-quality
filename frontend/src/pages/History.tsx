import { useEffect, useState } from 'react';
import {
  Container, Typography,
  CircularProgress, Alert, FormControl, InputLabel, Select, MenuItem, Box,
} from '@mui/material';
import { getScans, type Scan } from '../api/scans';
import ScanTable from '../components/ScanTable';

export default function History() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    getScans(50)
      .then(setScans)
      .catch((err) => {
        console.error('History load failed', err);
        setError('Failed to load scan history');
      })
      .finally(() => setLoading(false));
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
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  const filtered = statusFilter === 'all'
    ? scans
    : scans.filter((s) => s.status === statusFilter);

  return (
    <Container sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Scan History</Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
            <MenuItem value="cancelled">Cancelled</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {filtered.length === 0 ? (
        <Alert severity="info">No scans found.</Alert>
      ) : (
        <ScanTable scans={filtered} showId />
      )}
    </Container>
  );
}
