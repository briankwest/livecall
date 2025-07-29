import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Box, Container, Tab, Tabs, Typography, Grid, Stack } from '@mui/material';
import { Phone, History, Upload } from '@mui/icons-material';
import { CallHistory } from '../components/CallHistory';
import { LiveCallTab } from '../components/LiveCallTab';
import { DocumentsTab } from '../components/DocumentsTab';
import { Header } from '../components/Header';
import { WebPhone } from '../components/WebPhone';
import { CallInfo } from '../components/LiveCall/CallInfo';
import { useQuery } from '@tanstack/react-query';
import { callsService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../hooks/useWebSocket';
import { Call, WebSocketMessage } from '../types';
import { signalWireService } from '../services/signalwire';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export const HomePage: React.FC = () => {
  const location = useLocation();
  const [tabValue, setTabValue] = useState(0);
  const { user } = useAuth();
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [keepCallVisible, setKeepCallVisible] = useState(false);

  // Fetch active call
  const { data: activeCalls } = useQuery({
    queryKey: ['calls', 'active'],
    queryFn: () => callsService.listCalls({ status: 'active', limit: 1 }),
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
    refetchInterval: false,
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (activeCalls && activeCalls.length > 0) {
      setActiveCall(activeCalls[0]);
      setKeepCallVisible(true);
    } else if (!keepCallVisible) {
      setActiveCall(null);
    }
  }, [activeCalls, keepCallVisible]);

  // Listen for WebPhone call ended event
  useEffect(() => {
    const handleWebPhoneCallEnded = () => {
      console.log('HomePage: WebPhone call ended, marking call as ended');
      // Immediately mark the call as ended in the UI
      if (activeCall && activeCall.status === 'active') {
        setActiveCall({ ...activeCall, status: 'ended' });
      }
    };

    signalWireService.on('call.ended', handleWebPhoneCallEnded);

    return () => {
      signalWireService.off('call.ended', handleWebPhoneCallEnded);
    };
  }, [activeCall]);

  // WebSocket message handler
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    console.log('HomePage received WebSocket message:', message.event, message.data);
    
    switch (message.event) {
      case 'call:status':
        // Check if this status update is for our active call
        if (activeCall && message.data.call_id === activeCall.id) {
          console.log(`Updating active call status to: ${message.data.status}`);
          if (message.data.status === 'ended') {
            // Update the active call to show it has ended
            setActiveCall({ ...activeCall, status: 'ended' });
          } else if (message.data.status === 'active') {
            // Update to active status
            setActiveCall({ ...activeCall, status: 'active' });
          }
        }
        break;
    }
  };

  // Listen to WebSocket events for call status updates
  useWebSocket('general', {
    onMessage: handleWebSocketMessage,
  });

  // Handle tab query parameter
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab === '1') {
      setTabValue(1);
      // Scroll to top when navigating to live call tab
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [location]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Scroll to top when switching tabs
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Header />
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            Real-time Call Assistant
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI-powered assistance for live customer calls
          </Typography>
        </Box>

      <Grid container spacing={3}>
        {/* Left Column - WebPhone and Call Info (always visible) */}
        <Grid item xs={12} md={2.5}>
          <Stack spacing={2}>
            <WebPhone />
            {activeCall && (
              <CallInfo
                call={activeCall}
                agentUsername={user?.username}
                onCloseCall={() => {
                  setActiveCall(null);
                  setKeepCallVisible(false);
                }}
              />
            )}
          </Stack>
        </Grid>

        {/* Right Column - Tab Content */}
        <Grid item xs={12} md={9.5}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="homepage tabs">
              <Tab icon={<History />} label="Calls" />
              <Tab icon={<Phone />} label="Live Call" />
              <Tab icon={<Upload />} label="Documents" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <CallHistory />
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <LiveCallTab />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <DocumentsTab />
          </TabPanel>
        </Grid>
      </Grid>
    </Container>
    </>
  );
};