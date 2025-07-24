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
      // Don't create call records here - let the call-state webhook handle it
      // This prevents duplicate call records
      
      if (callState.direction === 'outbound' && callState.state === 'trying') {
        // Just navigate to live call tab
        navigate('/?tab=1');
        enqueueSnackbar('Placing call...', { variant: 'info' });
      } else if (callState.direction === 'inbound' && callState.state === 'answered') {
        // Just navigate to live call tab
        navigate('/?tab=1');
      }

      // Refresh active calls list after a short delay to allow webhook to create the call
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
      }, 1000);
    } catch (error) {
      console.error('Failed to sync call with backend:', error);
      enqueueSnackbar('Failed to sync call with system', { variant: 'error' });
    }
  }, [navigate, queryClient, enqueueSnackbar]);

  const handleCallEnded = useCallback(async (data: any) => {
    try {
      // The call-state webhook will handle marking the call as ended
      // We just need to refresh the UI
      
      // Refresh calls list
      queryClient.invalidateQueries({ queryKey: ['calls'] });
      queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
      
      enqueueSnackbar('Call ended', { variant: 'info' });
    } catch (error) {
      console.error('Failed to update UI after call ended:', error);
    }
  }, [queryClient, enqueueSnackbar]);

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