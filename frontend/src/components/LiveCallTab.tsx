import React, { useState, useEffect } from 'react';
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
import { WebPhone } from './WebPhone';
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
  const [aiSuggestions, setAiSuggestions] = useState<Document[]>([]);
  const [contextSummary, setContextSummary] = useState<string>('');
  const [contextTopics, setContextTopics] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [keepCallVisible, setKeepCallVisible] = useState(false);

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
      setActiveCall(activeCalls[0]);
      setKeepCallVisible(true);
    } else if (!keepCallVisible) {
      console.log('No active calls found and not keeping visible');
      setActiveCall(null);
      setTranscriptions([]);
      setAiSuggestions([]);
      setContextSummary('');
      setContextTopics([]);
    }
  }, [activeCalls, keepCallVisible]);

  // Fetch transcriptions for active call
  const { data: initialTranscriptions } = useQuery({
    queryKey: ['transcriptions', activeCall?.id],
    queryFn: () => activeCall ? callsService.getTranscripts(activeCall.id) : Promise.resolve([]),
    enabled: !!activeCall,
  });

  useEffect(() => {
    if (initialTranscriptions) {
      setTranscriptions(initialTranscriptions);
    }
  }, [initialTranscriptions]);

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

  // WebSocket message handler
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.event) {
      case 'transcription:update':
        const newTranscription: Transcription = {
          id: message.data.transcription_id,
          speaker: message.data.speaker === 'agent' ? 'agent' : 'customer',
          text: message.data.text,
          timestamp: message.data.timestamp,
          sentiment: message.data.sentiment,
          sentiment_score: message.data.sentiment_score,
        };
        setTranscriptions((prev) => [...prev, newTranscription]);
        
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

      case 'call:status':
        if (message.data.status === 'ended') {
          // Update the call status but keep it visible
          if (activeCall) {
            setActiveCall({ ...activeCall, status: 'ended' });
          }
          
          // Only invalidate if we don't have an active call to avoid unnecessary refetches
          if (!keepCallVisible) {
            queryClient.invalidateQueries({ queryKey: ['calls'] });
            queryClient.invalidateQueries({ queryKey: ['transcriptions'] });
          }
          
          enqueueSnackbar('Call has ended', { variant: 'info' });
        } else if (message.data.call_state === 'answered' || message.data.status === 'active') {
          // Update the active call to show it's answered
          if (activeCall) {
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
      setWsConnectionId(activeCall.id);
    } else if (!activeCall) {
      setWsConnectionId('general');
    }
  }, [activeCall?.id, activeCall?.status]);
  
  const { sendMessage } = useWebSocket(wsConnectionId, {
    onMessage: handleWebSocketMessage,
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
        {/* Left Column - WebPhone */}
        <Grid item xs={12} md={3}>
          <WebPhone />
          {activeCall && (
            <>
              <Box sx={{ mt: 2 }}>
                <CallInfo
                  call={activeCall}
                  agentUsername={user?.username}
                  onCloseCall={() => {
                    setActiveCall(null);
                    setTranscriptions([]);
                    setAiSuggestions([]);
                    setContextSummary('');
                    setContextTopics([]);
                    setKeepCallVisible(false);
                  }}
                />
              </Box>
            </>
          )}
        </Grid>

        {/* Middle and Right Columns - Call Details */}
        {activeCall ? (
          <>
            <Grid item xs={12} md={5} sx={{ height: '600px' }}>
              <TranscriptionPanel
                transcriptions={transcriptions}
                isLive={activeCall.status === 'active'}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <Stack spacing={2}>
                <SentimentSummary transcriptions={transcriptions} />
                <AIAssistancePanel
                  suggestions={aiSuggestions}
                  summary={contextSummary}
                  topics={contextTopics}
                  onDocumentClick={handleDocumentClick}
                  onFeedback={handleDocumentFeedback}
                />
              </Stack>
            </Grid>
          </>
        ) : (
          <Grid item xs={12} md={9}>
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