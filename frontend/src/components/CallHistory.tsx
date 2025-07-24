import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  TextField,
  MenuItem,
  Typography,
} from '@mui/material';
import {
  Visibility,
  Assessment,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { callsService } from '../services/api';
import { Call } from '../types';

export const CallHistory: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Fetch calls
  const { data: calls = [], isLoading } = useQuery({
    queryKey: ['calls', page, rowsPerPage, statusFilter],
    queryFn: () =>
      callsService.listCalls({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        status: statusFilter || undefined,
      }),
  });

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'ended':
        return 'default';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" gutterBottom>
          Call History
        </Typography>
        <Typography variant="body2" color="text.secondary">
          View and analyze past call recordings and summaries
        </Typography>
      </Box>

      <Paper elevation={2}>
        <Box sx={{ p: 2 }}>
          <TextField
            select
            label="Status Filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="ended">Ended</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </TextField>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Phone Number</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Start Time</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Mode</TableCell>
                <TableCell align="center">Transcriptions</TableCell>
                <TableCell align="center">Documents</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : calls.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    No calls found
                  </TableCell>
                </TableRow>
              ) : (
                calls.map((call) => (
                  <TableRow key={call.id} hover>
                    <TableCell>{call.phone_number || 'Unknown'}</TableCell>
                    <TableCell>{call.agent_id || '-'}</TableCell>
                    <TableCell>
                      <Chip
                        label={call.status}
                        size="small"
                        color={getStatusColor(call.status)}
                      />
                    </TableCell>
                    <TableCell>
                      {format(new Date(call.start_time), 'MMM d, HH:mm')}
                    </TableCell>
                    <TableCell>{formatDuration(call.duration_seconds)}</TableCell>
                    <TableCell>
                      <Chip
                        label={call.listening_mode}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="center">
                      {call.transcription_count || 0}
                    </TableCell>
                    <TableCell align="center">
                      {call.documents_accessed || 0}
                    </TableCell>
                    <TableCell align="center">
                      {call.status === 'active' ? (
                        <IconButton
                          size="small"
                          onClick={() => navigate('/?tab=1')}
                          title="View Live Call"
                        >
                          <Visibility />
                        </IconButton>
                      ) : (
                        <IconButton
                          size="small"
                          onClick={() => navigate(`/calls/${call.id}/summary`)}
                          title="View Summary"
                          disabled
                        >
                          <Assessment />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={-1} // We don't have total count from the API
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
    </>
  );
};