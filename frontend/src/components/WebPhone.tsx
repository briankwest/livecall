import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  TextField,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  CircularProgress,
} from '@mui/material';
import {
  Phone,
  PhoneDisabled,
  MicOff,
  Mic,
  Pause,
  PlayArrow,
  Dialpad,
  Close,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { signalWireService, CallState } from '../services/signalwire';
import { useAuth } from '../contexts/AuthContext';

export const WebPhone: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const { user } = useAuth();
  const [isInitializing, setIsInitializing] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [currentCall, setCurrentCall] = useState<CallState | null>(null);
  const [callDuration, setCallDuration] = useState(0);
  const [showDialpad, setShowDialpad] = useState(false);
  const [incomingCall, setIncomingCall] = useState<CallState | null>(null);

  // Initialize WebPhone when component mounts and user is authenticated
  useEffect(() => {
    console.log('WebPhone useEffect - user:', !!user, 'isInitialized:', isInitialized, 'isInitializing:', isInitializing);
    
    // Wait a bit for SignalWire SDK to load
    const checkAndInitialize = async () => {
      // Check if SignalWire SDK is loaded
      if (typeof SignalWire === 'undefined') {
        console.log('SignalWire SDK not loaded yet, waiting...');
        setTimeout(checkAndInitialize, 500);
        return;
      }
      
      console.log('SignalWire SDK is loaded');
      
      // Check if SignalWire service is already initialized
      if (signalWireService.isInitialized) {
        console.log('SignalWire service already initialized');
        setIsInitialized(true);
        setupEventHandlers();
      } else if (user && !isInitializing) {
        console.log('Initializing WebPhone...');
        initializeWebPhone();
      }
    };
    
    checkAndInitialize();

    return () => {
      // Don't disconnect on component unmount - keep connection alive
      // signalWireService.disconnect();
    };
  }, [user]); // Simplified dependencies to avoid loops

  const initializeWebPhone = async () => {
    console.log('initializeWebPhone called');
    setIsInitializing(true);
    try {
      console.log('Calling signalWireService.initialize()...');
      await signalWireService.initialize();
      console.log('SignalWire initialized successfully');
      setIsInitialized(true);
      setupEventHandlers();
      enqueueSnackbar('WebPhone initialized successfully', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar('Failed to initialize WebPhone', { variant: 'error' });
      console.error('WebPhone initialization error:', error);
      setIsInitialized(false);
    } finally {
      setIsInitializing(false);
    }
  };

  const setupEventHandlers = () => {
    signalWireService.on('call.received', (call: CallState) => {
      setIncomingCall(call);
      enqueueSnackbar(`Incoming call from ${call.phoneNumber}`, { variant: 'info' });
    });

    signalWireService.on('call.started', (call: CallState) => {
      setCurrentCall(call);
      setIncomingCall(null);
    });

    signalWireService.on('call.state', (data: any) => {
      setCurrentCall(prev => prev ? { ...prev, state: data.state } : null);
      
      if (data.state === 'answered') {
        setCurrentCall(prev => prev ? { ...prev, startTime: new Date() } : null);
      }
    });

    signalWireService.on('call.ended', () => {
      setCurrentCall(null);
      setCallDuration(0);
      enqueueSnackbar('Call ended', { variant: 'info' });
    });

    signalWireService.on('call.muted', (data: any) => {
      setCurrentCall(prev => prev ? { ...prev, muted: data.muted } : null);
    });

    signalWireService.on('call.hold', (data: any) => {
      setCurrentCall(prev => prev ? { ...prev, onHold: data.onHold } : null);
    });
  };

  // Update call duration timer
  useEffect(() => {
    if (currentCall?.startTime && currentCall.state === 'answered') {
      const interval = setInterval(() => {
        const duration = Math.floor((Date.now() - currentCall.startTime!.getTime()) / 1000);
        setCallDuration(duration);
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [currentCall?.startTime, currentCall?.state]);

  const handleMakeCall = async () => {
    if (!phoneNumber.trim()) {
      enqueueSnackbar('Please enter a phone number', { variant: 'warning' });
      return;
    }

    try {
      await signalWireService.makeCall(phoneNumber);
    } catch (error) {
      enqueueSnackbar('Failed to make call', { variant: 'error' });
    }
  };

  const handleAnswerCall = async () => {
    try {
      await signalWireService.answerCall();
      setIncomingCall(null);
      setCurrentCall(incomingCall);
    } catch (error) {
      enqueueSnackbar('Failed to answer call', { variant: 'error' });
    }
  };

  const handleRejectCall = async () => {
    try {
      await signalWireService.rejectCall();
      setIncomingCall(null);
    } catch (error) {
      enqueueSnackbar('Failed to reject call', { variant: 'error' });
    }
  };

  const handleHangup = async () => {
    try {
      await signalWireService.hangupCall();
    } catch (error) {
      enqueueSnackbar('Failed to hang up call', { variant: 'error' });
    }
  };

  const handleToggleMute = async () => {
    try {
      await signalWireService.toggleMute();
    } catch (error) {
      enqueueSnackbar('Failed to toggle mute', { variant: 'error' });
    }
  };

  const handleToggleHold = async () => {
    try {
      await signalWireService.toggleHold();
    } catch (error) {
      enqueueSnackbar('Failed to toggle hold', { variant: 'error' });
    }
  };

  const handleDialpadClick = (digit: string) => {
    if (currentCall) {
      signalWireService.sendDTMF(digit);
    } else {
      setPhoneNumber(prev => prev + digit);
    }
  };

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const getCallStateColor = (state: string) => {
    switch (state) {
      case 'trying':
      case 'ringing':
        return 'warning';
      case 'answered':
        return 'success';
      case 'ending':
      case 'ended':
        return 'error';
      default:
        return 'default';
    }
  };

  if (!user) {
    return (
      <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          Please log in to use the WebPhone
        </Typography>
      </Paper>
    );
  }

  // Always show the main UI - initialization happens in background
  // if (isInitializing) {
  //   return (
  //     <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
  //       <CircularProgress />
  //       <Typography variant="body2" sx={{ mt: 2 }}>
  //         Initializing WebPhone...
  //       </Typography>
  //     </Paper>
  //   );
  // }

  // if (!isInitialized && !isInitializing) {
  //   return (
  //     <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
  //       <Typography variant="body1" color="error">
  //         Failed to initialize WebPhone
  //       </Typography>
  //       <Button onClick={initializeWebPhone} sx={{ mt: 2 }}>
  //         Retry
  //       </Button>
  //     </Paper>
  //   );
  // }

  return (
    <>
      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          WebPhone
        </Typography>

        {/* Call Status */}
        {currentCall && (
          <Box sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {currentCall.direction === 'inbound' ? 'Incoming' : 'Outgoing'} Call
              </Typography>
              <Chip
                label={currentCall.state}
                size="small"
                color={getCallStateColor(currentCall.state)}
              />
            </Box>
            <Typography variant="h6">
              {currentCall.phoneNumber}
            </Typography>
            {currentCall.state === 'answered' && (
              <Typography variant="body2" color="text.secondary">
                {formatDuration(callDuration)}
              </Typography>
            )}
            {currentCall.onHold && (
              <Chip label="On Hold" size="small" color="warning" sx={{ mt: 1 }} />
            )}
          </Box>
        )}

        {/* Dialer */}
        {!currentCall && (
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              placeholder="+1 (555) 123-4567"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleMakeCall();
                }
              }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowDialpad(true)}>
                      <Dialpad />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Box>
        )}

        {/* Call Controls */}
        <Grid container spacing={2} justifyContent="center">
          {!currentCall ? (
            <Grid item>
              <Button
                variant="contained"
                color="success"
                size="large"
                startIcon={<Phone />}
                onClick={handleMakeCall}
                disabled={!phoneNumber.trim()}
              >
                Call
              </Button>
            </Grid>
          ) : (
            <>
              <Grid item>
                <IconButton
                  color={currentCall.muted ? 'error' : 'default'}
                  onClick={handleToggleMute}
                  title={currentCall.muted ? 'Unmute' : 'Mute'}
                >
                  {currentCall.muted ? <MicOff /> : <Mic />}
                </IconButton>
              </Grid>
              <Grid item>
                <IconButton
                  color={currentCall.onHold ? 'warning' : 'default'}
                  onClick={handleToggleHold}
                  title={currentCall.onHold ? 'Resume' : 'Hold'}
                >
                  {currentCall.onHold ? <PlayArrow /> : <Pause />}
                </IconButton>
              </Grid>
              <Grid item>
                <IconButton
                  onClick={() => setShowDialpad(true)}
                  title="Dialpad"
                >
                  <Dialpad />
                </IconButton>
              </Grid>
              <Grid item>
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={<PhoneDisabled />}
                  onClick={handleHangup}
                >
                  End Call
                </Button>
              </Grid>
            </>
          )}
        </Grid>

        {/* Hidden SignalWire container */}
        <div id="signalwire-container" style={{ display: 'none' }} />
      </Paper>

      {/* Incoming Call Dialog */}
      <Dialog open={!!incomingCall} onClose={() => {}} disableEscapeKeyDown>
        <DialogTitle>Incoming Call</DialogTitle>
        <DialogContent>
          <Typography variant="h6" align="center" sx={{ my: 2 }}>
            {incomingCall?.phoneNumber}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            color="error"
            variant="outlined"
            onClick={handleRejectCall}
          >
            Reject
          </Button>
          <Button
            color="success"
            variant="contained"
            onClick={handleAnswerCall}
          >
            Answer
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialpad Dialog */}
      <Dialog open={showDialpad} onClose={() => setShowDialpad(false)}>
        <DialogTitle>
          Dialpad
          <IconButton
            onClick={() => setShowDialpad(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={1} sx={{ width: 240 }}>
            {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((digit) => (
              <Grid item xs={4} key={digit}>
                <Button
                  fullWidth
                  variant="outlined"
                  sx={{ height: 60, fontSize: 24 }}
                  onClick={() => handleDialpadClick(digit)}
                >
                  {digit}
                </Button>
              </Grid>
            ))}
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
};