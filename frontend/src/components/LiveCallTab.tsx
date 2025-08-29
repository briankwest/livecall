import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Grid,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Stack,
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { CallInfo } from './LiveCall/CallInfo';
import { TranscriptionPanel } from './LiveCall/TranscriptionPanel';
import { AIAssistancePanel } from './LiveCall/AIAssistancePanel';
import { SentimentSummary } from './LiveCall/SentimentSummary';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebPhoneSync } from '../hooks/useWebPhoneSync';
import { useAuth } from '../contexts/AuthContext';
import { callsService, documentsService } from '../services/api';
import { signalWireService } from '../services/signalwire';
import {
  Call,
  Transcription,
  Document,
  AISuggestion,
  WebSocketMessage,
} from '../types';

export const LiveCallTab: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const hasLoadedInitialRef = useRef(false); // Track if we've loaded initial transcriptions
  const [aiSuggestions, setAiSuggestions] = useState<Document[]>([]);
  const [contextSummary, setContextSummary] = useState<string>('');
  const [contextTopics, setContextTopics] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [keepCallVisible, setKeepCallVisible] = useState(false);
  const [conversationSummary, setConversationSummary] = useState<string>('');

  // Sync WebPhone calls with backend
  useWebPhoneSync();

  // Fetch active call - no polling, rely on WebSocket updates
  const { data: activeCalls } = useQuery({
    queryKey: ['calls', 'active'],
    queryFn: () => callsService.listCalls({ status: 'active', limit: 1 }),
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    refetchInterval: false, // Disable automatic refetching
    refetchIntervalInBackground: false, // Disable background refetching
  });

  useEffect(() => {
    console.log('Active calls from backend:', activeCalls);
    if (activeCalls && activeCalls.length > 0) {
      console.log('Setting active call:', activeCalls[0]);
      // Check if this is a new call
      if (!activeCall || activeCall.id !== activeCalls[0].id) {
        hasLoadedInitialRef.current = false; // Reset the flag for new call
      }
      setActiveCall(activeCalls[0]);
      setKeepCallVisible(true);
    } else if (!keepCallVisible) {
      console.log('No active calls found and not keeping visible');
      // Only clear transcriptions if we don't have an active call
      // This prevents clearing during temporary connection issues
      if (!activeCall || activeCall.status === 'ended') {
        console.log('[DEBUG] Clearing call data as call has ended, had', transcriptions.length, 'transcriptions');
        setActiveCall(null);
        setTranscriptions([]);
        setAiSuggestions([]);
        setContextSummary('');
        setContextTopics([]);
        hasLoadedInitialRef.current = false; // Reset the flag
      } else {
        console.log('[DEBUG] NOT clearing transcriptions - activeCall exists with status:', activeCall?.status);
      }
    }
  }, [activeCalls, keepCallVisible, activeCall, transcriptions.length]);

  // Fetch transcriptions for active call
  const { data: initialTranscriptions } = useQuery({
    queryKey: ['transcriptions', activeCall?.id],
    queryFn: () => activeCall ? callsService.getTranscripts(activeCall.id) : Promise.resolve([]),
    enabled: !!activeCall,
  });

  useEffect(() => {
    // Only set initial transcriptions once per call and if we don't have any yet
    // This prevents overwriting live WebSocket transcriptions with stale backend data
    if (initialTranscriptions && !hasLoadedInitialRef.current && transcriptions.length === 0) {
      console.log('[DEBUG] Loading initial transcriptions from backend:', initialTranscriptions.length);
      setTranscriptions(initialTranscriptions);
      hasLoadedInitialRef.current = true;
    } else if (initialTranscriptions && transcriptions.length > 0) {
      console.log('[DEBUG] Skipping initial transcriptions load - already have', transcriptions.length, 'live transcriptions');
    }
  }, [initialTranscriptions, transcriptions.length]); // Include transcriptions.length to check current state

  // End call mutation
  const endCallMutation = useMutation({
    mutationFn: (callId: string) => callsService.endCall(callId),
    onSuccess: () => {
      enqueueSnackbar('Call ended successfully', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: ['calls'] });
      setActiveCall(null);
    },
    onError: () => {
      enqueueSnackbar('Failed to end call', { variant: 'error' });
    },
  });


  // REMOVED: Summary generation every 5 transcriptions - was blocking transcription flow

  // WebSocket message handler
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    console.log('WebSocket message received:', message.event);
    
    switch (message.event) {
      case 'transcription:update':
        console.log('[DEBUG] Transcription update received:', {
          id: message.data.transcription_id,
          text: message.data.text?.substring(0, 50) + '...',
          currentCount: transcriptions.length
        });
        
        const newTranscription: Transcription = {
          id: message.data.transcription_id,
          speaker: message.data.speaker === 'agent' ? 'agent' : 'customer',
          text: message.data.text,
          timestamp: message.data.timestamp,
          sentiment: message.data.sentiment,
          sentiment_score: message.data.sentiment_score,
        };
        
        setTranscriptions((prev) => {
          const newCount = prev.length + 1;
          console.log(`[DEBUG] Adding transcription #${newCount}, previous count: ${prev.length}`);
          if (newCount === 5) {
            console.log('[WARNING] Reached 5 transcriptions - checking for issues...');
          }
          if (newCount === 6) {
            console.log('[SUCCESS] Passed 5 transcriptions - system working correctly');
          }
          if (newCount > 10) {
            console.log(`[SUCCESS] ${newCount} transcriptions received and displayed`);
          }
          return [...prev, newTranscription];
        });
        
        // If we receive transcriptions, the call must be active
        if (activeCall && activeCall.status !== 'active') {
          setActiveCall({ ...activeCall, status: 'active' });
        }
        break;

      case 'ai:suggestion':
        const suggestion = message.data as AISuggestion;
        setAiSuggestions(suggestion.documents);
        setContextSummary(suggestion.summary);
        setContextTopics(suggestion.topics);
        break;

      case 'conversation:summary':
        setConversationSummary(message.data.summary);
        break;

      case 'call:status':
        // Check if this status update is for our active call
        if (activeCall && message.data.call_id === activeCall.id) {
          if (message.data.status === 'ended') {
            // Update the call status but keep it visible
            setActiveCall({ ...activeCall, status: 'ended' });
            setKeepCallVisible(true); // Keep the call visible after it ends
            
            // Only invalidate if we don't have an active call to avoid unnecessary refetches
            if (!keepCallVisible) {
              queryClient.invalidateQueries({ queryKey: ['calls'] });
              queryClient.invalidateQueries({ queryKey: ['transcriptions'] });
            }
            
            enqueueSnackbar('Call has ended - Click "Close Call" to clear', { variant: 'info' });
          } else if (message.data.call_state === 'answered' || message.data.status === 'active') {
            // Update the active call to show it's answered
            setActiveCall({ ...activeCall, status: 'active' });
          } else {
            // Only invalidate if we don't have an active call yet
            queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
          }
        } else if (message.data.call_state === 'created' || message.data.call_state === 'ringing') {
          // Only invalidate if we don't have an active call yet
          if (!activeCall) {
            queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
          }
        }
        break;

      case 'connection:success':
        enqueueSnackbar('Connected to real-time updates', { variant: 'success' });
        break;
    }
  };

  // WebSocket connection - use a stable connection ID
  // Don't switch between 'general' and call ID too frequently
  const [wsConnectionId, setWsConnectionId] = useState<string>('general');
  
  useEffect(() => {
    // Only switch to call-specific connection when we have a stable active call
    if (activeCall?.id && activeCall.status === 'active') {
      // Only change if it's actually different to avoid reconnections
      if (wsConnectionId !== activeCall.id) {
        console.log(`Switching WebSocket connection from ${wsConnectionId} to ${activeCall.id}`);
        setWsConnectionId(activeCall.id);
      }
    } else if (!activeCall && wsConnectionId !== 'general') {
      console.log(`Switching WebSocket connection from ${wsConnectionId} to general`);
      setWsConnectionId('general');
    }
  }, [activeCall?.id, activeCall?.status, wsConnectionId]);
  
  const { sendMessage } = useWebSocket(wsConnectionId, {
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log(`WebSocket connected for: ${wsConnectionId}`);
    },
    onDisconnect: () => {
      console.log(`WebSocket disconnected for: ${wsConnectionId}`);
    },
  });

  // Handle document click
  const handleDocumentClick = async (docId: string) => {
    try {
      const doc = await documentsService.getDocument(docId);
      setSelectedDocument(doc);
    } catch (error) {
      enqueueSnackbar('Failed to load document', { variant: 'error' });
    }
  };

  // Handle document feedback
  const handleDocumentFeedback = (docId: string, helpful: boolean) => {
    if (activeCall) {
      sendMessage('doc:feedback', { doc_id: docId, helpful, call_id: activeCall.id });
      enqueueSnackbar('Feedback submitted', { variant: 'success' });
    }
  };

  return (
    <>
      <Grid container spacing={3}>

        {/* Call Details */}
        {activeCall ? (
          <>
            <Grid item xs={12} md={7} sx={{ height: { xs: '400px', md: '600px', lg: '700px' }, minHeight: '400px' }}>
              <TranscriptionPanel
                transcriptions={transcriptions}
                isLive={activeCall.status === 'active'}
              />
            </Grid>

            <Grid item xs={12} md={5}>
              <Stack spacing={2}>
                <CallInfo 
                  call={activeCall}
                  agentUsername={user?.username}
                  onCloseCall={async () => {
                    // If call is still active, end it first
                    if (activeCall && activeCall.status === 'active') {
                      try {
                        await endCallMutation.mutateAsync(activeCall.id);
                      } catch (error) {
                        console.error('Failed to end call:', error);
                      }
                    }
                    
                    // Clear the UI
                    setKeepCallVisible(false);
                    setActiveCall(null);
                    setTranscriptions([]);
                    setAiSuggestions([]);
                    setContextSummary('');
                    setContextTopics([]);
                    queryClient.invalidateQueries({ queryKey: ['calls'] });
                  }}
                />
                <SentimentSummary transcriptions={transcriptions} />
                <AIAssistancePanel
                  suggestions={aiSuggestions}
                  summary={contextSummary}
                  topics={contextTopics}
                  conversationSummary={conversationSummary}
                  onDocumentClick={handleDocumentClick}
                  onFeedback={handleDocumentFeedback}
                />
              </Stack>
            </Grid>
          </>
        ) : (
          <Grid item xs={12}>
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom>
                No Active Call
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Use the WebPhone to make or receive a call. Live transcription and AI assistance will appear here.
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>

      {/* Document Viewer Dialog */}
      <Dialog
        open={!!selectedDocument}
        onClose={() => setSelectedDocument(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedDocument && (
          <>
            <DialogTitle>{selectedDocument.title}</DialogTitle>
            <DialogContent>
              <Box sx={{ whiteSpace: 'pre-wrap' }}>{selectedDocument.content}</Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedDocument(null)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </>
  );
};