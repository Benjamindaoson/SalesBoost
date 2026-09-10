import { useEffect, useRef, useState } from 'react';
import { Card, Input, Button, Avatar, Spin, message } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons';
import { chatApi } from '../services/api';
import type { Message } from '../types';

interface ChatViewProps {
  sessionId: string;
  aiDriving: boolean;
  onSendMessage?: (content: string) => void;
}

export default function ChatView({ sessionId, aiDriving, onSendMessage }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load history
  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const response = await chatApi.getHistory(sessionId);
        setMessages(response.data);
      } catch (error) {
        console.error('Failed to load chat history:', error);
        message.error('加载聊天记录失败');
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [sessionId]);

  // SSE connection for real-time messages
  useEffect(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create new SSE connection
    const eventSource = new EventSource(`/api/chat/${sessionId}/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const newMessage: Message = JSON.parse(event.data);
        setMessages((prev) => [...prev, newMessage]);
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const content = inputValue.trim();
    setInputValue('');
    setSending(true);

    try {
      await chatApi.sendMessage(sessionId, content);
      onSendMessage?.(content);

      // Optimistically add user message
      const userMessage: Message = {
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        is_ai_generated: false
      };
      setMessages((prev) => [...prev, userMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      message.error('发送失败，请重试');
      setInputValue(content); // Restore input
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Card
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
    >
      {/* Messages area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        background: '#f5f5f5'
      }}>
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              style={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                marginBottom: 16
              }}
            >
              {!isUser && (
                <Avatar
                  icon={<RobotOutlined />}
                  style={{ background: '#1890ff', marginRight: 8 }}
                />
              )}
              <div style={{
                maxWidth: '70%',
                background: isUser ? '#1890ff' : 'white',
                color: isUser ? 'white' : 'black',
                padding: '12px 16px',
                borderRadius: 8,
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}>
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {msg.content}
                </div>
                <div style={{
                  fontSize: 11,
                  marginTop: 4,
                  opacity: 0.7,
                  textAlign: 'right'
                }}>
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN')}
                </div>
              </div>
              {isUser && (
                <Avatar
                  icon={<UserOutlined />}
                  style={{ background: '#52c41a', marginLeft: 8 }}
                />
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: 16,
        borderTop: '1px solid #f0f0f0',
        background: 'white'
      }}>
        {!aiDriving && (
          <div style={{
            marginBottom: 8,
            padding: '8px 12px',
            background: '#fff7e6',
            border: '1px solid #ffd591',
            borderRadius: 4,
            fontSize: 12,
            color: '#d46b08'
          }}>
            当前为人工控制模式，您发送的消息将直接发送给客户
          </div>
        )}
        <Input.Search
          placeholder="输入消息..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onSearch={handleSend}
          enterButton={
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={sending}
            >
              发送
            </Button>
          }
          size="large"
          disabled={sending}
        />
      </div>
    </Card>
  );
}
