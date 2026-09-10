import { useEffect, useState } from 'react';
import { Card, Button, Spin, Tag } from 'antd';
import { BulbOutlined, CheckOutlined } from '@ant-design/icons';
import { sessionsApi } from '../services/api';
import type { AISuggestion as AISuggestionType } from '../types';

interface AISuggestionProps {
  sessionId: string;
  visible: boolean;
  onAdopt?: (suggestion: string) => void;
}

export default function AISuggestion({
  sessionId,
  visible,
  onAdopt
}: AISuggestionProps) {
  const [suggestion, setSuggestion] = useState<AISuggestionType | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) return;

    const fetchSuggestion = async () => {
      setLoading(true);
      try {
        const response = await sessionsApi.getSuggestion(sessionId);
        setSuggestion(response.data);
      } catch (error) {
        console.error('Failed to fetch AI suggestion:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSuggestion();

    // Poll every 3 seconds
    const interval = setInterval(fetchSuggestion, 3000);

    return () => clearInterval(interval);
  }, [sessionId, visible]);

  if (!visible) return null;

  return (
    <Card
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        width: 400,
        maxHeight: 500,
        overflow: 'auto',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 1000
      }}
      title={
        <span>
          <BulbOutlined style={{ color: '#faad14', marginRight: 8 }} />
          AI 建议
        </span>
      }
      size="small"
    >
      {loading && !suggestion ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Spin />
        </div>
      ) : suggestion ? (
        <>
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontWeight: 500, marginBottom: 8 }}>建议话术：</p>
            <p style={{
              background: '#f0f2f5',
              padding: 12,
              borderRadius: 4,
              whiteSpace: 'pre-wrap'
            }}>
              {suggestion.suggestion}
            </p>
          </div>

          {suggestion.tactics && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontWeight: 500, marginBottom: 8 }}>策略分析：</p>
              <div style={{ marginBottom: 8 }}>
                <Tag color="blue">{suggestion.tactics.primary}</Tag>
                <Tag>{suggestion.tactics.tone}</Tag>
              </div>
              {suggestion.tactics.secondary && suggestion.tactics.secondary.length > 0 && (
                <div style={{ fontSize: 12, color: '#666' }}>
                  辅助策略: {suggestion.tactics.secondary.join(', ')}
                </div>
              )}
              {suggestion.tactics.avoid && suggestion.tactics.avoid.length > 0 && (
                <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
                  避免: {suggestion.tactics.avoid.join(', ')}
                </div>
              )}
            </div>
          )}

          <Button
            type="primary"
            icon={<CheckOutlined />}
            block
            onClick={() => onAdopt?.(suggestion.suggestion)}
          >
            采纳建议
          </Button>
        </>
      ) : (
        <p style={{ color: '#999', textAlign: 'center' }}>暂无建议</p>
      )}
    </Card>
  );
}
