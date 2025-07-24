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
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { CallInfo } from './LiveCall/CallInfo';
import { TranscriptionPanel } from './LiveCall/TranscriptionPanel';
import { AIAssistancePanel } from './LiveCall/AIAssistancePanel';
import { WebPhone } from './WebPhone';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebPhoneSync } from '../hooks/useWebPhoneSync';
import { callsService, documentsService } from '../services/api';
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

  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [aiSuggestions, setAiSuggestions] = useState<Document[]>([]);
  const [contextSummary, setContextSummary] = useState<string>('');
  const [contextTopics, setContextTopics] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);

  // Sync WebPhone calls with backend
  useWebPhoneSync();

  // Fetch active call
  const { data: activeCalls } = useQuery({
    queryKey: ['calls', 'active'],
    queryFn: () => callsService.listCalls({ status: 'active', limit: 1 }),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (activeCalls && activeCalls.length > 0) {
      setActiveCall(activeCalls[0]);
    } else {
      setActiveCall(null);
      setTranscriptions([]);
      setAiSuggestions([]);
      setContextSummary('');
      setContextTopics([]);
    }
  }, [activeCalls]);

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
        };
        setTranscriptions((prev) => [...prev, newTranscription]);
        break;

      case 'ai:suggestion':
        const suggestion = message.data as AISuggestion;
        setAiSuggestions(suggestion.documents);
        setContextSummary(suggestion.summary);
        setContextTopics(suggestion.topics);
        break;

      case 'call:status':
        if (message.data.status === 'ended') {
          queryClient.invalidateQueries({ queryKey: ['calls'] });
          enqueueSnackbar('Call has ended', { variant: 'info' });
          setActiveCall(null);
        }
        break;

      case 'connection:success':
        enqueueSnackbar('Connected to real-time updates', { variant: 'success' });
        break;
    }
  };

  // WebSocket connection - only connect when there's an active call
  const { sendMessage } = useWebSocket(activeCall?.id, {
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
            <Box sx={{ mt: 2 }}>
              <CallInfo
                call={activeCall}
                onEndCall={() => endCallMutation.mutate(activeCall.id)}
                isEnding={endCallMutation.isPending}
              />
            </Box>
          )}
        </Grid>

        {/* Middle and Right Columns - Call Details */}
        {activeCall ? (
          <>
            <Grid item xs={12} md={5}>
              <TranscriptionPanel
                transcriptions={transcriptions}
                isLive={activeCall.status === 'active'}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <AIAssistancePanel
                suggestions={aiSuggestions}
                summary={contextSummary}
                topics={contextTopics}
                onDocumentClick={handleDocumentClick}
                onFeedback={handleDocumentFeedback}
              />
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