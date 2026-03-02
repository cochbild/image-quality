import { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, List, ListItemButton, ListItemIcon, ListItemText,
  Typography, Box, Breadcrumbs, Link, Chip, TextField,
  CircularProgress,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ComputerIcon from '@mui/icons-material/Computer';
import ImageIcon from '@mui/icons-material/Image';
import { getDrives, browseDirectory, type Drive, type BrowseResult } from '../api/filesystem';

interface FolderPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
  currentPath: string;
  title?: string;
}

export default function FolderPicker({ open, onClose, onSelect, currentPath, title = 'Select Folder' }: FolderPickerProps) {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [browseResult, setBrowseResult] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [manualPath, setManualPath] = useState(currentPath);
  const [showDrives, setShowDrives] = useState(false);

  useEffect(() => {
    if (open) {
      getDrives().then(setDrives).catch(() => {});
      if (currentPath) {
        navigateTo(currentPath);
      } else {
        setShowDrives(true);
      }
      setManualPath(currentPath);
    }
  }, [open, currentPath]);

  const navigateTo = async (path: string) => {
    setLoading(true);
    setShowDrives(false);
    try {
      const result = await browseDirectory(path);
      setBrowseResult(result);
      setManualPath(result.path);
    } catch {
      // If browse fails, show drives
      setShowDrives(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = () => {
    onSelect(manualPath);
    onClose();
  };

  const handleManualSubmit = () => {
    navigateTo(manualPath);
  };

  // Parse path into breadcrumb segments
  const pathSegments = browseResult?.path
    ? browseResult.path.split(/[\\/]/).filter(Boolean)
    : [];

  const directories = browseResult?.entries.filter(e => e.type === 'directory') ?? [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {/* Manual path input */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            size="small"
            fullWidth
            value={manualPath}
            onChange={(e) => setManualPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleManualSubmit()}
            placeholder="Type a path or browse below"
          />
          <Button variant="outlined" size="small" onClick={handleManualSubmit}>Go</Button>
        </Box>

        {/* Breadcrumbs */}
        {browseResult && !showDrives && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Button
              size="small"
              startIcon={<ComputerIcon />}
              onClick={() => setShowDrives(true)}
            >
              Drives
            </Button>
            {browseResult.parent !== browseResult.path && (
              <Button
                size="small"
                startIcon={<ArrowUpwardIcon />}
                onClick={() => navigateTo(browseResult.parent)}
              >
                Up
              </Button>
            )}
            <Breadcrumbs sx={{ flex: 1 }}>
              {pathSegments.map((seg, i) => {
                const fullPath = pathSegments.slice(0, i + 1).join('\\');
                const isLast = i === pathSegments.length - 1;
                return isLast ? (
                  <Typography key={i} color="text.primary" variant="body2" fontWeight="bold">{seg}</Typography>
                ) : (
                  <Link
                    key={i}
                    component="button"
                    variant="body2"
                    onClick={() => navigateTo(fullPath + '\\')}
                    underline="hover"
                  >
                    {seg}
                  </Link>
                );
              })}
            </Breadcrumbs>
            {browseResult.image_count !== undefined && browseResult.image_count > 0 && (
              <Chip
                icon={<ImageIcon />}
                label={`${browseResult.image_count} images`}
                size="small"
                color="info"
              />
            )}
          </Box>
        )}

        {loading ? (
          <Box sx={{ textAlign: 'center', py: 3 }}><CircularProgress /></Box>
        ) : showDrives ? (
          <List dense>
            {drives.map((drive) => (
              <ListItemButton key={drive.path} onClick={() => navigateTo(drive.path)}>
                <ListItemIcon><ComputerIcon /></ListItemIcon>
                <ListItemText primary={drive.label} secondary={drive.path} />
              </ListItemButton>
            ))}
          </List>
        ) : (
          <List dense sx={{ maxHeight: 350, overflow: 'auto' }}>
            {directories.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
                No subdirectories
              </Typography>
            )}
            {directories.map((entry) => (
              <ListItemButton key={entry.path} onDoubleClick={() => navigateTo(entry.path)}>
                <ListItemIcon><FolderIcon color="primary" /></ListItemIcon>
                <ListItemText primary={entry.name} />
              </ListItemButton>
            ))}
          </List>
        )}

        {browseResult?.error && (
          <Typography color="error" variant="body2">{browseResult.error}</Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSelect}>
          Select This Folder
        </Button>
      </DialogActions>
    </Dialog>
  );
}
