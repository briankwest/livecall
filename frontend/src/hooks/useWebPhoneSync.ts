import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { signalWireService, CallState } from '../services/signalwire';
import { callsService } from '../services/api';

export const useWebPhoneSync = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const syncCallWithBackend = useCallback(async (callState: CallState) => {
    try {
      if (callState.direction === 'outbound' && callState.state === 'trying') {
        // Create call record in backend when outbound call starts
        const response = await callsService.initiateCall({
          to_number: callState.phoneNumber,
          agent_name: 'WebPhone User', // TODO: Get from auth context
          listening_mode: 'both',
          webrtc_call_id: callState.id,
        });

        // Navigate to live call tab
        navigate('/?tab=1');
      } else if (callState.direction === 'inbound' && callState.state === 'answered') {
        // For inbound calls, create record when answered
        const response = await callsService.initiateCall({
          to_number: 'Inbound',
          from_number: callState.phoneNumber,
          agent_name: 'WebPhone User',
          listening_mode: 'both',
          webrtc_call_id: callState.id,
          direction: 'inbound',
        });

        // Navigate to live call tab
        navigate('/?tab=1');
      }

      // Refresh active calls list
      queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
    } catch (error) {
      console.error('Failed to sync call with backend:', error);
      enqueueSnackbar('Failed to sync call with system', { variant: 'error' });
    }
  }, [navigate, queryClient, enqueueSnackbar]);

  const handleCallEnded = useCallback(async (data: any) => {
    try {
      // Find the call by WebRTC ID and end it
      const calls = await callsService.listCalls({ 
        webrtc_call_id: data.id,
        status: 'active' 
      });

      if (calls.length > 0) {
        await callsService.endCall(calls[0].id);
      }

      // Refresh calls list
      queryClient.invalidateQueries({ queryKey: ['calls'] });
    } catch (error) {
      console.error('Failed to end call in backend:', error);
    }
  }, [queryClient]);

  useEffect(() => {
    // Set up event listeners
    signalWireService.on('call.started', syncCallWithBackend);
    signalWireService.on('call.ended', handleCallEnded);

    // Clean up listeners
    return () => {
      signalWireService.off('call.started', syncCallWithBackend);
      signalWireService.off('call.ended', handleCallEnded);
    };
  }, [syncCallWithBackend, handleCallEnded]);
};

export default useWebPhoneSync;