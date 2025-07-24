import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage } from '../types';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export const useWebSocket = (
  callId: string | null | undefined,
  options: UseWebSocketOptions = {}
) => {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Don't connect if no callId or if already connected
    if (!callId || callId === 'null' || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('No auth token available');
      return;
    }

    // Build WebSocket URL based on environment
    const baseUrl = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${baseUrl}//${host}/ws?call_id=${callId}&token=${token}`;
    
    console.log(`Connecting WebSocket for call: ${callId}`);
    
    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        onConnect?.();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        onDisconnect?.();

        // Only auto-reconnect if we still have a valid callId
        if (autoReconnect && callId && callId !== 'null') {
          console.log(`Will attempt to reconnect in ${reconnectInterval}ms`);
          reconnectTimeoutRef.current = setTimeout(() => {
            // Double-check callId is still valid before reconnecting
            if (callId && callId !== 'null') {
              connect();
            }
          }, reconnectInterval);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  }, [callId, onMessage, onConnect, onDisconnect, autoReconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((event: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event, data }));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    // Only connect if we have a valid callId
    if (callId && callId !== 'null') {
      connect();
    } else {
      // If no callId, ensure we're disconnected
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [callId]); // Remove connect and disconnect from dependencies to prevent loops

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};