import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Button,
  Stack,
  CircularProgress,
} from '@mui/material';
import {
  Phone,
  Timer,
  Person,
  Headset,
  Stop,
} from '@mui/icons-material';
import { format, formatDuration, intervalToDuration } from 'date-fns';
import { Call } from '../../types';

interface CallInfoProps {
  call: Call;
  agentUsername?: string;
  onCloseCall?: () => void;
}

export const CallInfo: React.FC<CallInfoProps> = ({
  call,
  agentUsername,
  onCloseCall,
}) => {
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

  const getDuration = () => {
    if (call.duration_seconds) {
      return formatDuration(
        intervalToDuration({ start: 0, end: call.duration_seconds * 1000 })
      );
    }
    if (call.status === 'active') {
      return 'Ongoing';
    }
    return 'N/A';
  };

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ flex: 1 }}>
          Call Information
        </Typography>
        <Chip
          label={call.status}
          color={getStatusColor(call.status)}
          size="small"
        />
      </Box>

      <Stack spacing={2}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Phone fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary">
            Phone Number:
          </Typography>
          <Typography variant="body2">
            {call.phone_number || 'Unknown'}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Person fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary">
            Agent:
          </Typography>
          <Typography variant="body2">{agentUsername || call.agent_id || 'N/A'}</Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Timer fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary">
            Duration:
          </Typography>
          <Typography variant="body2">{getDuration()}</Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Headset fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary">
            Listening Mode:
          </Typography>
          <Chip label={call.listening_mode} size="small" variant="outlined" />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Phone fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary">
            Direction:
          </Typography>
          <Chip 
            label={call.direction} 
            size="small" 
            variant="outlined"
            color={call.direction === 'outbound' ? 'primary' : 'secondary'}
          />
        </Box>

        <Box>
          <Typography variant="body2" color="text.secondary">
            Started:
          </Typography>
          <Typography variant="body2">
            {format(new Date(call.start_time), 'PPpp')}
          </Typography>
        </Box>

        {call.transcription_count !== undefined && (
          <Box>
            <Typography variant="body2" color="text.secondary">
              Transcriptions: {call.transcription_count}
            </Typography>
          </Box>
        )}

        {call.documents_accessed !== undefined && (
          <Box>
            <Typography variant="body2" color="text.secondary">
              Documents Accessed: {call.documents_accessed}
            </Typography>
          </Box>
        )}
      </Stack>

      {/* Show Close Call button - enabled only when call has ended */}
      {onCloseCall && (
        <Button
          variant="contained"
          color="primary"
          onClick={onCloseCall}
          disabled={call.status !== 'ended'}
          fullWidth
          sx={{ mt: 3 }}
        >
          Close Call
        </Button>
      )}
    </Paper>
  );
};