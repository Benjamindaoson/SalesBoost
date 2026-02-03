import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
  error?: string;
  // Dynamic fields from backend
  history?: any[];
  npc_response?: string;
  coach_tip?: any;
  message?: string;
  content?: string;
  [key: string]: any;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
  connectionAttempts: number;
}

export interface WebSocketOptions {
  url?: string;
  queryParams?: Record<string, string>;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export function useWebSocket(options: WebSocketOptions = {}) {
  const {
    url = 'ws://localhost:8000/ws/train',
    queryParams = {},
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    onConnect,
    onDisconnect,
    onError,
    onMessage,
  } = options;

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    connectionAttempts: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<any[]>([]);

  // Construct URL with query parameters
  const getUrlWithParams = useCallback(() => {
    if (!url) return '';
    const params = new URLSearchParams(queryParams);
    const queryString = params.toString();
    return queryString ? `${url}?${queryString}` : url;
  }, [url, queryParams]);

  // Clean up function
  const cleanup = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Send heartbeat
  const startHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }

    heartbeatRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  // Connect WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const fullUrl = getUrlWithParams();
    if (!fullUrl) return;

    setState(prev => ({
      ...prev,
      isConnecting: true,
      error: null,
    }));

    try {
      const ws = new WebSocket(fullUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          connectionAttempts: 0,
        }));

        // Send queued messages
        messageQueueRef.current.forEach(message => {
          ws.send(JSON.stringify(message));
        });
        messageQueueRef.current = [];

        startHeartbeat();
        onConnect?.();
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
        }));

        cleanup();
        onDisconnect?.();

        // Auto reconnect
        if (state.connectionAttempts < reconnectAttempts && event.code !== 1000) {
          setState(prev => ({
            ...prev,
            connectionAttempts: prev.connectionAttempts + 1,
          }));

          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (${state.connectionAttempts + 1}/${reconnectAttempts})`);
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({
          ...prev,
          error: 'WebSocket connection error',
          isConnecting: false,
        }));

        onError?.(error);
        toast.error('WebSocket connection failed');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Handle heartbeat pong
          if (message.type === 'pong') {
            return;
          }

          setState(prev => ({
            ...prev,
            lastMessage: message,
          }));

          onMessage?.(message);

          // Handle error messages from server
          if (message.error || message.type === 'error') {
            const errorMsg = message.error || (message.data && message.data.message) || 'Unknown error';
            toast.error(errorMsg);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to create WebSocket connection',
        isConnecting: false,
      }));
    }
  }, [getUrlWithParams, reconnectAttempts, reconnectInterval, state.connectionAttempts, onConnect, onDisconnect, onError, onMessage, startHeartbeat, cleanup]);

  // Disconnect
  const disconnect = useCallback(() => {
    cleanup();
    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      lastMessage: null,
      connectionAttempts: 0,
    });
  }, [cleanup]);

  // Send message
  const sendMessage = useCallback((message: any) => {
    const messageWithTimestamp = {
      ...message,
      timestamp: Date.now(),
    };

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(messageWithTimestamp));
    } else {
      // Queue message if not connected
      messageQueueRef.current.push(messageWithTimestamp);
      
      if (!state.isConnecting && !state.isConnected) {
        connect();
      }
    }
  }, [state.isConnecting, state.isConnected, connect]);

  // Send sales message
  const sendSalesMessage = useCallback((content: string, sessionId: string) => {
    sendMessage({
      type: 'message', // Changed from 'sales_message' to match backend expectation 'message' or 'text'
      content: content,
      session_id: sessionId,
    });
  }, [sendMessage]);

  // Auto connect on mount
  useEffect(() => {
    connect();

    return () => {
      cleanup();
    };
  }, [connect, cleanup]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    sendSalesMessage,
    websocket: wsRef.current,
  };
}
