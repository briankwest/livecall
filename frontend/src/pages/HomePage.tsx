import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Box, Container, Tab, Tabs, Typography } from '@mui/material';
import { Phone, History } from '@mui/icons-material';
import { CallHistory } from '../components/CallHistory';
import { LiveCallTab } from '../components/LiveCallTab';
import { Header } from '../components/Header';

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

  // Handle tab query parameter
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab === '1') {
      setTabValue(1);
    }
  }, [location]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <>
      <Header />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            Real-time Call Assistant
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI-powered assistance for live customer calls
          </Typography>
        </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="homepage tabs">
          <Tab icon={<History />} label="Calls" />
          <Tab icon={<Phone />} label="Live Call" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <CallHistory />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <LiveCallTab />
      </TabPanel>
    </Container>
    </>
  );
};