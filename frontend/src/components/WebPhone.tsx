import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import { callsService } from '../services/api';
import { Call } from '../types';

interface WebPhoneProps {
  onCallStart?: () => void;
}

export const WebPhone: React.FC<WebPhoneProps> = ({ onCallStart }) => {
  const { enqueueSnackbar } = useSnackbar();
  const { user } = useAuth();
  const [isInitializing, setIsInitializing] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [currentCall, setCurrentCall] = useState<CallState | null>(null);
  const [callDuration, setCallDuration] = useState(0);
  const [showDialpad, setShowDialpad] = useState(false);
  const [incomingCall, setIncomingCall] = useState<CallState | null>(null);
  const [isCallInProgress, setIsCallInProgress] = useState(false);
  const initRef = useRef(false);

  // Define event handlers
  const handleCallReceived = useCallback((call: CallState) => {
    setIncomingCall(call);
    enqueueSnackbar(`Incoming call from ${call.phoneNumber}`, { variant: 'info' });
  }, [enqueueSnackbar]);

  const handleCallStarted = useCallback((call: CallState) => {
    setCurrentCall(call);
    setIncomingCall(null);
    setIsCallInProgress(true);
  }, []);

  const handleCallState = useCallback((data: any) => {
    console.log('Call state event received:', data);
    
    setCurrentCall(prev => {
      if (!prev) return null;
      // Ensure state is a valid CallState state value
      const validStates = ['new', 'requesting', 'trying', 'active', 'hangup', 'destroy'] as const;
      const newState = validStates.includes(data.state) ? data.state : prev.state;
      return { ...prev, state: newState };
    });
    
    if (data.state === 'active') {
      setCurrentCall(prev => prev ? { ...prev, startTime: new Date() } : null);
      setIsCallInProgress(false); // Call is now connected, not "in progress"
      enqueueSnackbar('Call connected', { variant: 'success' });
    } else if (data.state === 'trying') {
      // Call is being setup
      enqueueSnackbar('Connecting call...', { variant: 'info' });
    } else if (data.state === 'hangup') {
      // Call is ending
      console.log('Call state is hangup - call will be destroyed soon');
    }
  }, [enqueueSnackbar]);

  const handleCallEnded = useCallback(() => {
    console.log('WebPhone: call.ended event received - RESETTING TO IDLE STATE');
    setCurrentCall(null);
    setIncomingCall(null);  // Also clear incoming call
    setCallDuration(0);
    setIsCallInProgress(false);
    setPhoneNumber('');  // Clear the phone number field
    enqueueSnackbar('Call ended', { variant: 'info' });
    console.log('WebPhone: Reset complete - should be in idle state now');
  }, [enqueueSnackbar]);

  const handleCallMuted = useCallback((data: any) => {
    setCurrentCall(prev => {
      if (!prev) return null;
      return { ...prev, muted: data.muted };
    });
  }, []);

  const handleCallHold = useCallback((data: any) => {
    setCurrentCall(prev => {
      if (!prev) return null;
      return { ...prev, onHold: data.onHold };
    });
  }, []);

  const handleConnectionLost = useCallback(() => {
    enqueueSnackbar('WebPhone connection lost. Reconnecting...', { variant: 'warning' });
  }, [enqueueSnackbar]);

  const handleConnectionRestored = useCallback(() => {
    enqueueSnackbar('WebPhone connection restored', { variant: 'success' });
  }, [enqueueSnackbar]);

  const setupEventHandlers = useCallback(() => {
    console.log('Setting up WebPhone event handlers');
    
    // Remove any existing handlers first to prevent duplicates
    signalWireService.off('call.received', handleCallReceived);
    signalWireService.off('call.started', handleCallStarted);
    signalWireService.off('call.state', handleCallState);
    signalWireService.off('call.ended', handleCallEnded);
    signalWireService.off('call.muted', handleCallMuted);
    signalWireService.off('call.hold', handleCallHold);
    signalWireService.off('connection.lost', handleConnectionLost);
    signalWireService.off('connection.restored', handleConnectionRestored);
    
    // Add the handlers
    signalWireService.on('call.received', handleCallReceived);
    signalWireService.on('call.started', handleCallStarted);
    signalWireService.on('call.state', handleCallState);
    signalWireService.on('call.ended', handleCallEnded);
    signalWireService.on('call.muted', handleCallMuted);
    signalWireService.on('call.hold', handleCallHold);
    signalWireService.on('connection.lost', handleConnectionLost);
    signalWireService.on('connection.restored', handleConnectionRestored);
  }, [handleCallReceived, handleCallStarted, handleCallState, handleCallEnded, handleCallMuted, handleCallHold, handleConnectionLost, handleConnectionRestored]);

  // Initialize WebPhone when component mounts and user is authenticated
  useEffect(() => {
    if (!user || initRef.current) return;
    
    // Mark as initialized to prevent double init
    initRef.current = true;
    
    // Simple ready function like client.js
    const ready = (callback: () => void) => {
      if (document.readyState != 'loading') {
        callback();
      } else {
        document.addEventListener('DOMContentLoaded', callback);
      }
    };
    
    ready(() => {
      console.log('WebPhone ready');
      if (!signalWireService.isInitialized && !isInitializing) {
        initializeWebPhone();
      }
    });

    return () => {
      // Clean up event handlers on unmount
      signalWireService.off('call.received', handleCallReceived);
      signalWireService.off('call.started', handleCallStarted);
      signalWireService.off('call.state', handleCallState);
      signalWireService.off('call.ended', handleCallEnded);
      signalWireService.off('call.muted', handleCallMuted);
      signalWireService.off('call.hold', handleCallHold);
      signalWireService.off('connection.lost', handleConnectionLost);
      signalWireService.off('connection.restored', handleConnectionRestored);
    };
  }, [user, handleCallReceived, handleCallStarted, handleCallState, handleCallEnded, handleCallMuted, handleCallHold, handleConnectionLost, handleConnectionRestored]);

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
    } catch (error: any) {
      const errorMessage = error?.message || 'Unknown error occurred';
      console.error('WebPhone initialization error:', error);
      
      // Show more specific error messages
      if (errorMessage.includes('SignalWire SDK not loaded')) {
        enqueueSnackbar('SignalWire SDK failed to load', { variant: 'error' });
      } else if (errorMessage.includes('token')) {
        enqueueSnackbar('Authentication failed - invalid token', { variant: 'error' });
      } else if (errorMessage.includes('online')) {
        enqueueSnackbar('Failed to connect to SignalWire service', { variant: 'error' });
      } else {
        enqueueSnackbar(`WebPhone initialization failed: ${errorMessage}`, { variant: 'error' });
      }
      
      setIsInitialized(false);
    } finally {
      setIsInitializing(false);
    }
  };

  // Update call duration timer only
  useEffect(() => {
    if (currentCall && currentCall.startTime && currentCall.state === 'active') {
      const durationInterval = setInterval(() => {
        const duration = Math.floor((Date.now() - currentCall.startTime!.getTime()) / 1000);
        setCallDuration(duration);
      }, 1000);

      return () => {
        clearInterval(durationInterval);
      };
    }
  }, [currentCall]);

  const handleMakeCall = async () => {
    if (!phoneNumber.trim()) {
      enqueueSnackbar('Please enter a phone number', { variant: 'warning' });
      return;
    }

    if (isCallInProgress) {
      enqueueSnackbar('Call already in progress', { variant: 'warning' });
      return;
    }

    setIsCallInProgress(true);
    try {
      console.log('WebPhone: Calling makeCall...');
      await signalWireService.makeCall(phoneNumber);
      console.log('WebPhone: makeCall completed successfully');
      // Switch to Live Call tab when call starts
      if (onCallStart) {
        onCallStart();
      }
    } catch (error) {
      console.error('WebPhone: makeCall failed:', error);
      enqueueSnackbar(`Failed to make call: ${error instanceof Error ? error.message : 'Unknown error'}`, { variant: 'error' });
      setIsCallInProgress(false);
    }
  };

  const handleAnswerCall = async () => {
    try {
      console.log('User clicked Answer button for incoming call');
      await signalWireService.answerCall();
      // The call.started event will handle setting currentCall
      // Just clear the incoming call dialog
      setIncomingCall(null);
      // Switch to Live Call tab when answering a call
      if (onCallStart) {
        onCallStart();
      }
    } catch (error) {
      console.error('Failed to answer call:', error);
      enqueueSnackbar(`Failed to answer call: ${error instanceof Error ? error.message : 'Unknown error'}`, { variant: 'error' });
    }
  };

  const handleRejectCall = async () => {
    try {
      console.log('User clicked Reject button for incoming call');
      await signalWireService.rejectCall();
      setIncomingCall(null);
    } catch (error) {
      console.error('Failed to reject call:', error);
      enqueueSnackbar(`Failed to reject call: ${error instanceof Error ? error.message : 'Unknown error'}`, { variant: 'error' });
    }
  };

  const handleHangup = async () => {
    try {
      await signalWireService.hangupCall();
      
      // Also notify the backend to end the call
      // This ensures the Call Information tab gets updated
      if (currentCall) {
        try {
          // Get the active call from the backend
          const activeCalls = await callsService.listCalls({ status: 'active' });
          const backendCall = activeCalls.length > 0 ? activeCalls[0] : null;
          
          if (backendCall) {
            await callsService.endCall(backendCall.id);
            console.log('Backend call ended successfully');
          }
        } catch (apiError) {
          console.error('Failed to end call in backend:', apiError);
          // Don't show error to user as the WebPhone hangup was successful
        }
      }
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
      case 'new':
      case 'requesting':
      case 'trying':
        return 'warning';
      case 'active':
        return 'success';
      case 'hangup':
      case 'destroy':
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            WebPhone
          </Typography>
          {!isInitialized && (
            <>
              <Chip 
                label={isInitializing ? "Initializing..." : "Not Connected"} 
                size="small" 
                color={isInitializing ? "warning" : "error"}
              />
              {!isInitializing && (
                <Button 
                  size="small" 
                  onClick={initializeWebPhone}
                  sx={{ ml: 1 }}
                >
                  Retry
                </Button>
              )}
            </>
          )}
          {isInitialized && (
            <Chip 
              label="Connected" 
              size="small" 
              color="success"
            />
          )}
        </Box>

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
            {currentCall.state === 'active' && (
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
                disabled={!phoneNumber.trim() || isCallInProgress || (!isInitialized && !isInitializing)}
              >
                {isCallInProgress ? 'Calling...' : isInitializing ? 'Initializing...' : 'Call'}
              </Button>
            </Grid>
          ) : (
            <>
              {/* Only show mute, hold, and dialpad when call is active */}
              {currentCall.state === 'active' && (
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
                </>
              )}
              {/* Always show End Call button when there's a call */}
              <Grid item>
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={<PhoneDisabled />}
                  onClick={handleHangup}
                  disabled={currentCall.state === 'hangup' || currentCall.state === 'destroy'}
                >
                  End Call
                </Button>
              </Grid>
            </>
          )}
        </Grid>

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