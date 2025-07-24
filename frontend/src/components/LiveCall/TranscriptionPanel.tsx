import React, { useEffect, useRef, useState } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Chip, 
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { Transcription } from '../../types';

interface TranscriptionPanelProps {
  transcriptions: Transcription[];
  isLive: boolean;
}

export const TranscriptionPanel: React.FC<TranscriptionPanelProps> = ({
  transcriptions,
  isLive,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [selectedTranscription, setSelectedTranscription] = useState<Transcription | null>(null);
  const [openModal, setOpenModal] = useState(false);

  // Auto-scroll to bottom when new transcriptions arrive
  useEffect(() => {
    if (isLive) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcriptions, isLive]);

  const handleTranscriptionClick = (transcription: Transcription) => {
    setSelectedTranscription(transcription);
    setOpenModal(true);
  };

  const handleCloseModal = () => {
    setOpenModal(false);
    setSelectedTranscription(null);
  };

  return (
    <>
      <Paper
        elevation={2}
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">Transcription</Typography>
        {isLive && <LinearProgress sx={{ mt: 1 }} />}
      </Box>

      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {transcriptions.length === 0 ? (
          <Typography color="text.secondary" align="center">
            Waiting for transcriptions...
          </Typography>
        ) : (
          transcriptions.map((transcription) => (
            <Box
              key={transcription.id}
              sx={{
                display: 'flex',
                gap: 2,
                alignItems: 'flex-start',
              }}
            >
              <Chip
                label={transcription.speaker}
                size="small"
                color={transcription.speaker === 'agent' ? 'primary' : 'secondary'}
                sx={{ minWidth: 80 }}
              />
              <Box 
                sx={{ 
                  flex: 1,
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'action.hover',
                    borderRadius: 1,
                    padding: 1,
                    margin: -1,
                  }
                }}
                onClick={() => handleTranscriptionClick(transcription)}
              >
                <Typography 
                  variant="body1"
                  sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {transcription.text}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {format(new Date(transcription.timestamp), 'HH:mm:ss')}
                  {transcription.confidence && (
                    <> • {Math.round(transcription.confidence * 100)}% confidence</>
                  )}
                </Typography>
              </Box>
            </Box>
          ))
        )}
        <div ref={bottomRef} />
      </Box>
    </Paper>

    {/* Transcription Detail Modal */}
    <Dialog
      open={openModal}
      onClose={handleCloseModal}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6">Transcription Details</Typography>
            {selectedTranscription && (
              <Chip
                label={selectedTranscription.speaker}
                size="small"
                color={selectedTranscription.speaker === 'agent' ? 'primary' : 'secondary'}
              />
            )}
          </Box>
          <IconButton onClick={handleCloseModal} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {selectedTranscription && (
          <Box>
            <Typography variant="body1" paragraph>
              {selectedTranscription.text}
            </Typography>
            <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>Time:</strong> {format(new Date(selectedTranscription.timestamp), 'PPpp')}
              </Typography>
              {selectedTranscription.confidence && (
                <Typography variant="body2" color="text.secondary">
                  <strong>Confidence:</strong> {Math.round(selectedTranscription.confidence * 100)}%
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                <strong>Speaker:</strong> {selectedTranscription.speaker === 'agent' ? 'Agent' : 'Customer'}
              </Typography>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseModal}>Close</Button>
      </DialogActions>
    </Dialog>
    </>
  );
};