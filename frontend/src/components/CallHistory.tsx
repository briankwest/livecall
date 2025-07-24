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
  Button,
  TextField,
  MenuItem,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
  CircularProgress,
} from '@mui/material';
import { Visibility, Assessment } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { callsService } from '../services/api';
import { Call, Transcription } from '../types';

export const CallHistory: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);
  const [transcriptModalOpen, setTranscriptModalOpen] = useState(false);

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

  // Fetch transcriptions for selected call
  const { data: transcriptions = [], isLoading: loadingTranscripts } = useQuery({
    queryKey: ['transcriptions', selectedCall?.id],
    queryFn: () => selectedCall ? callsService.getTranscripts(selectedCall.id) : Promise.resolve([]),
    enabled: !!selectedCall,
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

  const handleViewCall = (call: Call) => {
    if (call.status === 'active') {
      navigate('/?tab=1');
    } else {
      setSelectedCall(call);
      setTranscriptModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setTranscriptModalOpen(false);
    setSelectedCall(null);
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
                <TableCell>Direction</TableCell>
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
                  <TableCell colSpan={10} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : calls.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    No calls found
                  </TableCell>
                </TableRow>
              ) : (
                calls.map((call) => (
                  <TableRow key={call.id} hover>
                    <TableCell>{call.phone_number || 'Unknown'}</TableCell>
                    <TableCell>
                      <Chip
                        label={call.direction}
                        size="small"
                        variant="outlined"
                        color={call.direction === 'outbound' ? 'primary' : 'secondary'}
                      />
                    </TableCell>
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
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => handleViewCall(call)}
                      >
                        {call.status === 'active' ? 'View Live' : 'View'}
                      </Button>
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
          count={-1}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      {/* Transcript Modal */}
      <Dialog
        open={transcriptModalOpen}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Call Transcripts
          {selectedCall && (
            <Typography variant="body2" color="text.secondary">
              {selectedCall.phone_number} • {format(new Date(selectedCall.start_time), 'PPp')}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent dividers>
          {loadingTranscripts ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : transcriptions.length === 0 ? (
            <Typography color="text.secondary" align="center">
              No transcriptions available for this call.
            </Typography>
          ) : (
            <List>
              {transcriptions.map((transcript, index) => (
                <React.Fragment key={transcript.id}>
                  {index > 0 && <Divider />}
                  <ListItem alignItems="flex-start">
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Chip
                            label={transcript.speaker}
                            size="small"
                            color={transcript.speaker === 'agent' ? 'primary' : 'secondary'}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(transcript.timestamp), 'HH:mm:ss')}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Typography variant="body2" color="text.primary">
                          {transcript.text}
                        </Typography>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};