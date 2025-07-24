import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography, Chip, LinearProgress } from '@mui/material';
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

  // Auto-scroll to bottom when new transcriptions arrive
  useEffect(() => {
    if (isLive) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcriptions, isLive]);

  return (
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
              <Box sx={{ flex: 1 }}>
                <Typography variant="body1">{transcription.text}</Typography>
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
  );
};