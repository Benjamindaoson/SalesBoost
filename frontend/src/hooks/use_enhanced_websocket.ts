/**
 * Enhanced WebSocket Hook with Advanced Connection Management
 * 强化WebSocket连接管理，实现企业级稳定性
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
  error?: string;
  seq_id?: string; // 新增序列号
  requires_ack?: boolean; // 是否需要确认
}

export interface ConnectionState {
  is_connected: boolean;
  is_connecting: boolean;
  is_reconnecting: boolean;
  error: string | null;
  last_message: WebSocketMessage | null;
  connection_attempts: number;
  quality: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown';
  server_url: string;
  latency_ms: number;
  uptime_seconds: number;
  last_ping: number;
}

export interface EnhancedWebSocketOptions {
  url?: string;
  query_params?: Record<string, string>;
  reconnect_attempts?: number;
  reconnect_interval?: number;
  heartbeat_interval?: number;
  on_connect?: () => void;
  on_disconnect?: () => void;
  on_error?: (error: Event) => void;
  on_message?: (message: WebSocketMessage) => void;
  on_quality_change?: (quality: string) => void;
  on_latency_update?: (latency: number) => void;
  timeout_ms?: number;
  ping_timeout?: number;
  enable_ack?: boolean;
}

export function use_enhanced_websocket(options: EnhancedWebSocketOptions = {}) {
  const {
    url = 'ws://localhost:8000/ws/train',
    query_params = {},
    reconnect_attempts = 5,
    reconnect_interval = 3000,
    heartbeat_interval = 30000,
    on_connect,
    on_disconnect,
    on_error,
    on_message,
    on_quality_change,
    on_latency_update,
    timeout_ms = 10000,
    ping_timeout = 5000,
    enable_ack = true,
  } = options;

  const [state, setState] = useState<ConnectionState>({
    is_connected: false,
    is_connecting: false,
    is_reconnecting: false,
    error: null,
    last_message: null,
    connection_attempts: 0,
    quality: 'unknown',
    server_url: url,
    latency_ms: 0,
    uptime_seconds: 0,
    last_ping: 0,
  });

  const ws_ref = useRef<WebSocket | null>(null);
  const reconnect_timer_ref = useRef<NodeJS.Timeout | null>(null);
  const heartbeat_timer_ref = useRef<NodeJS.Timeout | null>(null);
  const ping_timer_ref = useRef<NodeJS.Timeout | null>(null);
  const connection_start_ref = useRef<number>(0);
  const message_queue_ref = useRef<Array<{id: string, data: any, timestamp: number, retry_count: number}>>([]);
  const ack_tracker_ref = useRef<Map<string, {timestamp: number, retry_count: number}>>(new Map());
  const latency_history_ref = useRef<number[]>([]);
  const message_handlers_ref = useRef<Map<string, (data: any) => void>>(new Map());

  // 构建完整URL
  const build_websocket_url = useCallback(() => {
    const url_obj = new URL(url);
    Object.entries(query_params).forEach(([key, value]) => {
      url_obj.searchParams.set(key, value);
    });
    return url_obj.toString();
  }, [url, query_params]);

  // 评估连接质量
  const assess_connection_quality = useCallback((latency: number, error_count: number) => {
    if (error_count === 0 && latency < 100) return 'excellent';
    if (error_count === 0 && latency < 300) return 'good';
    if (error_count < 3 && latency < 1000) return 'fair';
    return 'poor';
  }, []);

  // 生成消息ID
  const generate_message_id = useCallback(() => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // 发送带确认的消息
  const send_message_with_ack = useCallback((message: any, requires_ack: boolean = false) => {
    if (!ws_ref.current || state.is_connected !== true) {
      message_queue_ref.current.push({
        id: generate_message_id(),
        data: message,
        timestamp: Date.now(),
        retry_count: 0,
      });
      return;
    }

    const message_id = generate_message_id();
    const full_message: WebSocketMessage = {
      type: 'user_message',
      data: message,
      timestamp: Date.now(),
      seq_id: message_id,
      requires_ack,
    };

    if (requires_ack && enable_ack) {
      ack_tracker_ref.current.set(message_id, {
        timestamp: Date.now(),
        retry_count: 0,
      });
    }

    ws_ref.current.send(JSON.stringify(full_message));
  }, [state.is_connected, enable_ack]);

  // 处理ACK接收
  const handle_ack_received = useCallback((seq_id: string) => {
    const ack_info = ack_tracker_ref.current.get(seq_id);
    if (ack_info) {
      ack_tracker_ref.current.delete(seq_id);
    }
  }, []);

  // 处理消息队列
  const process_message_queue = useCallback(() => {
    if (message_queue_ref.current.length > 0 && state.is_connected) {
      const message = message_queue_ref.current.shift();
      send_message_with_ack(message.data, false);
    }
  }, [state.is_connected]);

  // 心跳检测
  const start_heartbeat = useCallback(() => {
    if (heartbeat_timer_ref.current) {
      clearInterval(heartbeat_timer_ref.current);
    }

    heartbeat_timer_ref.current = setInterval(() => {
      if (ws_ref.current?.readyState === WebSocket.OPEN) {
        const ping_start = Date.now();
        const ping_id = generate_message_id();
        
        ping_timer_ref.current = setTimeout(() => {
          if (ack_tracker_ref.current.has(ping_id)) {
            const latency = Date.now() - ping_start;
            latency_history_ref.current.push(latency);
            
            // 保持最近10次延迟记录
            if (latency_history_ref.current.length > 10) {
              latency_history_ref.current = latency_history_ref.current.slice(-10);
            }

            const avg_latency = latency_history_ref.current.reduce((a, b) => a + b, 0) / latency_history_ref.current.length;
            const quality = assess_connection_quality(avg_latency, state.connection_attempts);

            setState(prev => ({
              ...prev,
              latency_ms: avg_latency,
              quality,
              last_ping: Date.now(),
            }));

            on_latency_update?.(avg_latency);
            on_quality_change?.(quality);
          }
        }, ping_timeout);

        ws_ref.current.send(JSON.stringify({
          type: 'ping',
          timestamp: ping_start,
          seq_id: ping_id,
        }));
      }
    }, heartbeat_interval);
  }, [heartbeat_interval, assess_connection_quality, on_latency_update, on_quality_change, ping_timeout, generate_message_id]);

  // 指数退避重连
  const attempt_reconnect = useCallback((delay_multiplier: number = 1) => {
    if (state.connection_attempts >= reconnect_attempts) {
      setState(prev => ({
        ...prev,
        error: 'Max reconnection attempts reached',
        is_reconnecting: false,
      }));
      toast.error('连接失败，请刷新页面重试');
      return;
    }

    const delay = reconnect_interval * Math.pow(2, Math.min(delay_multiplier - 1, 5)); // 指数退避，最大32x延迟
    
    reconnect_timer_ref.current = setTimeout(() => {
      setState(prev => ({
        ...prev,
        is_reconnecting: true,
        connection_attempts: prev.connection_attempts + 1,
      }));
      
      connect();
    }, delay);
  }, [reconnect_attempts, reconnect_interval]);

  // 连接WebSocket
  const connect = useCallback(() => {
    if (ws_ref.current) {
      ws_ref.current.close();
    }

    setState(prev => ({
      ...prev,
      is_connecting: true,
      error: null,
    }));

    try {
      const ws_url = build_websocket_url();
      ws_ref.current = new WebSocket(ws_url);
      
      connection_start_ref.current = Date.now();

      ws_ref.current.onopen = () => {
        setState(prev => ({
          ...prev,
          is_connected: true,
          is_connecting: false,
          is_reconnecting: false,
          error: null,
          connection_attempts: 0,
          quality: 'unknown',
          uptime_seconds: 0,
        }));

        // 处理消息队列
        process_message_queue();
        
        on_connect?.();
        
        // 启动心跳
        start_heartbeat();
        
        toast.success('WebSocket连接已建立');
      };

      ws_ref.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          setState(prev => ({
            ...prev,
            last_message: message,
            uptime_seconds: Date.now() - connection_start_ref.current,
          }));

          // 处理ACK
          if (message.type === 'ack' && message.seq_id) {
            handle_ack_received(message.seq_id);
          }

          on_message?.(message);
          
          // 处理消息处理器
          if (message.seq_id && message_handlers_ref.current.has(message.seq_id)) {
            const handler = message_handlers_ref.current.get(message.seq_id);
            if (handler) {
              handler(message.data);
              message_handlers_ref.current.delete(message.seq_id);
            }
          }
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
          setState(prev => ({...prev, error: 'Message parsing failed'}));
        }
      };

      ws_ref.current.onclose = (event) => {
        const quality = assess_connection_quality(
          latency_history_ref.current.length > 0 
            ? latency_history_ref.current.reduce((a, b) => a + b, 0) / latency_history_ref.current.length 
            : 0,
          state.connection_attempts
        );

        setState(prev => ({
          ...prev,
          is_connected: false,
          is_connecting: false,
          is_reconnecting: false,
          quality,
        }));

        if (heartbeat_timer_ref.current) {
          clearInterval(heartbeat_timer_ref.current);
          heartbeat_timer_ref.current = null;
        }

        if (ping_timer_ref.current) {
          clearTimeout(ping_timer_ref.current);
          ping_timer_ref.current = null;
        }

        // 清理ACK跟踪器中过期的消息
        const current_time = Date.now();
        for (const [seq_id, info] of ack_tracker_ref.current.entries()) {
          if (current_time - info.timestamp > 30000) { // 30秒超时
            ack_tracker_ref.current.delete(seq_id);
          }
        }

        on_disconnect?.();
        
        // 非正常关闭时尝试重连
        if (event.code !== 1000) {
          attempt_reconnect(state.connection_attempts + 1);
        } else {
          toast.info('连接已正常关闭');
        }
      };

      ws_ref.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({
          ...prev,
          error: `WebSocket error: ${error.type || 'Unknown'}`,
          is_connecting: false,
        }));

        on_error?.(error);
        toast.error('WebSocket连接错误');
      };

    } catch (error) {
      console.error('WebSocket connection error:', error);
      setState(prev => ({
        ...prev,
        error: `Connection failed: ${error}`,
        is_connecting: false,
      }));
      toast.error('无法建立WebSocket连接');
    }
  }, [build_websocket_url, assess_connection_quality, process_message_queue, attempt_reconnect, on_connect, on_disconnect, on_error, start_heartbeat, generate_message_id, handle_ack_received]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (ws_ref.current) {
      ws_ref.current.close(1000, 'Client disconnect');
      ws_ref.current = null;
    }

    if (reconnect_timer_ref.current) {
      clearTimeout(reconnect_timer_ref.current);
      reconnect_timer_ref.current = null;
    }

    if (heartbeat_timer_ref.current) {
      clearInterval(heartbeat_timer_ref.current);
      heartbeat_timer_ref.current = null;
    }

    if (ping_timer_ref.current) {
      clearTimeout(ping_timer_ref.current);
      ping_timer_ref.current = null;
    }

    // 清理所有计时器和跟踪器
    message_queue_ref.current = [];
    ack_tracker_ref.current.clear();
    latency_history_ref.current = [];
    message_handlers_ref.current.clear();

    setState({
      is_connected: false,
      is_connecting: false,
      is_reconnecting: false,
      error: null,
      last_message: null,
      connection_attempts: 0,
      quality: 'unknown',
      server_url: '',
      latency_ms: 0,
      uptime_seconds: 0,
      last_ping: 0,
    });
  }, []);

  // 发送用户消息
  const send_message = useCallback((message: any) => {
    send_message_with_ack(message, enable_ack);
  }, [send_message_with_ack, enable_ack]);

  // 发送请求并等待响应
  const send_request = useCallback(async (message: any, timeout: number = 10000) => {
    return new Promise((resolve, reject) => {
      const request_id = generate_message_id();
      
      // 设置响应处理器
      const timeout_handle = setTimeout(() => {
        message_handlers_ref.current.delete(request_id);
        reject(new Error('Request timeout'));
      }, timeout);

      message_handlers_ref.current.set(request_id, (response: any) => {
        clearTimeout(timeout_handle);
        resolve(response);
      });

      send_message_with_ack({
        ...message,
        request_id,
        timestamp: Date.now(),
      }, true);
    });
  }, [send_message_with_ack, generate_message_id]);

  // 组件挂载时连接
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  // 监听连接状态变化
  useEffect(() => {
    if (state.is_connected && message_queue_ref.current.length > 0) {
      process_message_queue();
    }
  }, [state.is_connected, process_message_queue]);

  return {
    ...state,
    send_message,
    send_request,
    disconnect,
    connect,
    reconnect: () => attempt_reconnect(1),
  };
}