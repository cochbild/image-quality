import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container, Typography, Card, CardContent, Button, Box, TextField,
  Table, TableHead, TableBody, TableRow, TableCell,
  LinearProgress, Chip, Alert, CircularProgress,
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import { startScan, getScan, type Scan } from '../api/scans';
import { getAssessmentsByScan, type Assessment } from '../api/assessments';
import { getAllSettings } from '../api/settings';
import ScoreChip from '../components/ScoreChip';

export default function ScanView() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const [scan, setScan] = useState<Scan | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New scan form
  const [inputDir, setInputDir] = useState('');
  const [outputDir, setOutputDir] = useState('');
  const [rejectDir, setRejectDir] = useState('');
  const [starting, setStarting] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load settings for directory defaults
  useEffect(() => {
    if (!scanId) {
      getAllSettings().then((s) => {
        setInputDir(s.input_dir || '');
        setOutputDir(s.output_dir || '');
        setRejectDir(s.reject_dir || '');
      }).catch((err) => console.error('Failed to load default directories', err));
    }
  }, [scanId]);

  // Load scan data and poll
  useEffect(() => {
    if (!scanId) return;

    const parsedId = Number(scanId);
    if (!Number.isFinite(parsedId) || parsedId <= 0) {
      setError(`Invalid scan id: ${scanId}`);
      setLoading(false);
      return;
    }

    // `cancelled` gates any state write after an effect teardown, preventing
    // a slow initial fetch from scheduling a poll after a new scanId has
    // already started its own effect run.
    let cancelled = false;

    const fetchOnce = async () => {
      const [s, a] = await Promise.all([
        getScan(parsedId),
        getAssessmentsByScan(parsedId),
      ]);
      if (cancelled) return null;
      setScan(s);
      setAssessments(a);
      return s;
    };

    setLoading(true);
    setError(null);

    fetchOnce()
      .then((s) => {
        if (cancelled || !s) return;
        if (s.status === 'running' && !pollRef.current) {
          pollRef.current = setInterval(() => {
            fetchOnce()
              .then((next) => {
                if (cancelled) return;
                if (next && next.status !== 'running' && pollRef.current) {
                  clearInterval(pollRef.current);
                  pollRef.current = null;
                }
              })
              .catch((err) => console.error('Poll failed', err));
          }, 3000);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('Failed to load scan', err);
        setError('Failed to load scan data');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [scanId]);

  const handleStartScan = async () => {
    setStarting(true);
    setError(null);
    try {
      const newScan = await startScan({
        input_dir: inputDir || undefined,
        output_dir: outputDir || undefined,
        reject_dir: rejectDir || undefined,
      });
      navigate(`/scan/${newScan.id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start scan';
      setError(message);
    } finally {
      setStarting(false);
    }
  };

  // New scan form
  if (!scanId) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>New Scan</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Input Directory"
                value={inputDir}
                onChange={(e) => setInputDir(e.target.value)}
                fullWidth
                helperText="Directory containing images to assess"
              />
              <TextField
                label="Output Directory"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                fullWidth
                helperText="Where passing images will be moved"
              />
              <TextField
                label="Reject Directory"
                value={rejectDir}
                onChange={(e) => setRejectDir(e.target.value)}
                fullWidth
                helperText="Where failing images will be moved"
              />
              <Button
                variant="contained"
                size="large"
                onClick={handleStartScan}
                disabled={starting}
              >
                {starting ? 'Starting...' : 'Start Scan'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Container>
    );
  }

  if (loading) {
    return (
      <Container sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  const progress = scan && scan.total_images > 0
    ? ((scan.passed_count + scan.failed_count) / scan.total_images) * 100
    : 0;

  return (
    <Container sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Scan #{scanId}</Typography>
        {scan && (
          <Chip
            label={scan.status}
            color={scan.status === 'completed' ? 'success' : scan.status === 'running' ? 'info' : 'default'}
          />
        )}
      </Box>

      {scan && scan.status === 'running' && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Processing: {scan.passed_count + scan.failed_count} / {scan.total_images} images
          </Typography>
          <LinearProgress variant="determinate" value={progress} />
        </Box>
      )}

      {scan && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <Chip label={`Total: ${scan.total_images}`} />
          <Chip label={`Passed: ${scan.passed_count}`} color="success" />
          <Chip label={`Failed: ${scan.failed_count}`} color="error" />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {assessments.length > 0 && (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell>Scores</TableCell>
                <TableCell>Result</TableCell>
                <TableCell>Deep Dive</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {assessments.map((a) => (
                <TableRow
                  key={a.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/assessment/${a.id}`)}
                >
                  <TableCell>{a.filename}</TableCell>
                  <TableCell>
                    {a.category_scores.map((cs) => (
                      <ScoreChip key={cs.category} category={cs.category} score={cs.score} />
                    ))}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={a.passed ? 'PASS' : 'FAIL'}
                      color={a.passed ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {a.category_scores.some((cs) => cs.was_deep_dive) && (
                      <ZoomInIcon color="info" fontSize="small" titleAccess="Deep dive triggered" />
                    )}
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
