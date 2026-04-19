import { useNavigate } from 'react-router-dom';
import {
  Card, Chip, Table, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import type { Scan } from '../api/scans';

const STATUS_COLORS: Record<string, 'success' | 'info' | 'error' | 'default'> = {
  completed: 'success',
  running: 'info',
  failed: 'error',
};

function statusColor(status: string) {
  return STATUS_COLORS[status] ?? 'default';
}

interface ScanTableProps {
  scans: Scan[];
  showId?: boolean;
}

export default function ScanTable({ scans, showId = false }: ScanTableProps) {
  const navigate = useNavigate();
  return (
    <Card>
      <Table>
        <TableHead>
          <TableRow>
            {showId && <TableCell>ID</TableCell>}
            <TableCell>Date</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Total</TableCell>
            <TableCell>Passed</TableCell>
            <TableCell>Failed</TableCell>
            <TableCell>Pass Rate</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {scans.map((scan) => (
            <TableRow
              key={scan.id}
              hover
              sx={{ cursor: 'pointer' }}
              onClick={() => navigate(`/scan/${scan.id}`)}
            >
              {showId && <TableCell>#{scan.id}</TableCell>}
              <TableCell>{new Date(scan.started_at).toLocaleString()}</TableCell>
              <TableCell>
                <Chip label={scan.status} color={statusColor(scan.status)} size="small" />
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
  );
}
