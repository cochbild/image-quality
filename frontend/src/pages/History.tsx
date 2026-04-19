import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container, Typography, Card, Table, TableHead, TableBody, TableRow, TableCell,
  Chip, CircularProgress, Alert, FormControl, InputLabel, Select, MenuItem, Box,
} from '@mui/material';
import { getScans, type Scan } from '../api/scans';

export default function History() {
  const navigate = useNavigate();
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
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Total</TableCell>
                <TableCell>Passed</TableCell>
                <TableCell>Failed</TableCell>
                <TableCell>Pass Rate</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((scan) => (
                <TableRow
                  key={scan.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/scan/${scan.id}`)}
                >
                  <TableCell>#{scan.id}</TableCell>
                  <TableCell>{new Date(scan.started_at).toLocaleString()}</TableCell>
                  <TableCell>
                    <Chip
                      label={scan.status}
                      color={
                        scan.status === 'completed' ? 'success'
                        : scan.status === 'running' ? 'info'
                        : scan.status === 'failed' ? 'error'
                        : 'default'
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{scan.total_images}</TableCell>
                  <TableCell>{scan.passed_count}</TableCell>
                  <TableCell>{scan.failed_count}</TableCell>
                  <TableCell>
                    {scan.total_images > 0
                      ? `${Math.round((scan.passed_count / scan.total_images) * 100)}%`
                      : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </Container>
  );
}
