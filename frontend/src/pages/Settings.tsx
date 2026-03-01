import { useEffect, useState } from 'react';
import {
  Container, Typography, Card, CardContent, TextField, Button, Box,
  Slider, Select, MenuItem, Chip, Divider, Snackbar, Alert,
  CircularProgress, InputLabel, FormControl,
} from '@mui/material';
import {
  getAllSettings, updateSetting,
  getLMStudioStatus, getLMStudioModels,
  type LMStudioStatus, type LMStudioModel,
} from '../api/settings';

const CATEGORIES = [
  { key: 'anatomical', label: 'Anatomical Integrity' },
  { key: 'compositional', label: 'Compositional Coherence' },
  { key: 'physics', label: 'Physics & Lighting' },
  { key: 'texture', label: 'Texture & Surface Quality' },
  { key: 'technical', label: 'Technical Quality' },
  { key: 'semantic', label: 'Semantic Integrity' },
];

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [lmStatus, setLmStatus] = useState<LMStudioStatus | null>(null);
  const [models, setModels] = useState<LMStudioModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });

  useEffect(() => {
    async function load() {
      try {
        const [settingsData, statusData] = await Promise.all([
          getAllSettings(),
          getLMStudioStatus(),
        ]);
        setSettings(settingsData);
        setLmStatus(statusData);
        if (statusData.connected) {
          const modelsData = await getLMStudioModels();
          setModels(modelsData);
        }
      } catch {
        setSnackbar({ open: true, message: 'Failed to load settings', severity: 'error' });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleChange = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const promises = Object.entries(settings).map(([key, value]) =>
        updateSetting(key, value)
      );
      await Promise.all(promises);
      setSnackbar({ open: true, message: 'Settings saved successfully', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'Failed to save settings', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Settings</Typography>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save All'}
        </Button>
      </Box>

      {/* LM Studio Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Typography variant="h6">LM Studio Connection</Typography>
            <Chip
              label={lmStatus?.connected ? 'Connected' : 'Disconnected'}
              color={lmStatus?.connected ? 'success' : 'error'}
              size="small"
            />
          </Box>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              label="LM Studio URL"
              value={settings.lm_studio_url || ''}
              onChange={(e) => handleChange('lm_studio_url', e.target.value)}
              fullWidth
            />
          </Box>
          <FormControl fullWidth>
            <InputLabel>Model</InputLabel>
            <Select
              value={settings.lm_studio_model || ''}
              label="Model"
              onChange={(e) => handleChange('lm_studio_model', e.target.value)}
            >
              <MenuItem value="">Auto-detect (first available)</MenuItem>
              {models.map((m) => (
                <MenuItem key={m.id} value={m.id}>{m.id}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </CardContent>
      </Card>

      {/* Directories Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Directories</Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Input Directory"
              value={settings.input_dir || ''}
              onChange={(e) => handleChange('input_dir', e.target.value)}
              fullWidth
            />
            <TextField
              label="Output Directory (passed images)"
              value={settings.output_dir || ''}
              onChange={(e) => handleChange('output_dir', e.target.value)}
              fullWidth
            />
            <TextField
              label="Reject Directory (failed images)"
              value={settings.reject_dir || ''}
              onChange={(e) => handleChange('reject_dir', e.target.value)}
              fullWidth
            />
          </Box>
        </CardContent>
      </Card>

      {/* Thresholds Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Category Thresholds</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Minimum score required to pass each category (1-10)
          </Typography>
          {CATEGORIES.map((cat) => (
            <Box key={cat.key} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography>{cat.label}</Typography>
                <Typography fontWeight="bold">
                  {settings[`threshold_${cat.key}`] || '5'}
                </Typography>
              </Box>
              <Slider
                value={parseInt(settings[`threshold_${cat.key}`] || '5')}
                onChange={(_, val) => handleChange(`threshold_${cat.key}`, String(val))}
                min={1}
                max={10}
                step={1}
                marks
                valueLabelDisplay="auto"
              />
            </Box>
          ))}
        </CardContent>
      </Card>

      {/* Triage Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Triage Settings</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Scores in the borderline zone trigger a deep-dive analysis
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>Borderline Zone Low</Typography>
              <Typography fontWeight="bold">{settings.borderline_low || '4'}</Typography>
            </Box>
            <Slider
              value={parseInt(settings.borderline_low || '4')}
              onChange={(_, val) => handleChange('borderline_low', String(val))}
              min={1}
              max={10}
              step={1}
              marks
              valueLabelDisplay="auto"
            />
          </Box>
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>Borderline Zone High</Typography>
              <Typography fontWeight="bold">{settings.borderline_high || '8'}</Typography>
            </Box>
            <Slider
              value={parseInt(settings.borderline_high || '8')}
              onChange={(_, val) => handleChange('borderline_high', String(val))}
              min={1}
              max={10}
              step={1}
              marks
              valueLabelDisplay="auto"
            />
          </Box>
        </CardContent>
      </Card>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
