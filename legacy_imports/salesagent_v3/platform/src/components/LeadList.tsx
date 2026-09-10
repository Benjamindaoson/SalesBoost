import { useQuery } from '@tanstack/react-query';
import { List, Badge, Tag, Spin, Empty } from 'antd';
import { FireOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import { sessionsApi } from '../services/api';
import type { Lead } from '../types';

interface LeadListProps {
  onSelectLead?: (sessionId: string) => void;
  selectedSessionId?: string;
}

export default function LeadList({ onSelectLead, selectedSessionId }: LeadListProps) {
  const { data: leads, isLoading } = useQuery({
    queryKey: ['activeSessions'],
    queryFn: async () => {
      const response = await sessionsApi.getActiveSessions();
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!leads || leads.length === 0) {
    return <Empty description="暂无活跃会话" />;
  }

  return (
    <List
      dataSource={leads}
      renderItem={(lead: Lead) => {
        const isHighIntent = lead.intent_score > 0.7;
        const isSelected = lead.session_id === selectedSessionId;

        return (
          <List.Item
            onClick={() => onSelectLead?.(lead.session_id)}
            style={{
              cursor: 'pointer',
              background: isSelected ? '#e6f7ff' : 'white',
              borderLeft: isSelected ? '3px solid #1890ff' : 'none',
              padding: '12px 16px',
              transition: 'all 0.3s'
            }}
            className="lead-list-item"
          >
            <List.Item.Meta
              avatar={
                <Badge count={lead.unread_count} offset={[-5, 5]}>
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    background: isHighIntent ? '#ff4d4f' : '#1890ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: 16,
                    fontWeight: 'bold'
                  }}>
                    {lead.customer_name.charAt(0)}
                  </div>
                </Badge>
              }
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontWeight: 500 }}>{lead.customer_name}</span>
                  {isHighIntent && (
                    <Tag color="red" icon={<FireOutlined />}>
                      高意向
                    </Tag>
                  )}
                  {lead.ai_driving ? (
                    <Tag color="blue" icon={<RobotOutlined />}>
                      AI 主驾
                    </Tag>
                  ) : (
                    <Tag color="orange" icon={<UserOutlined />}>
                      人工控制
                    </Tag>
                  )}
                </div>
              }
              description={
                <div>
                  <div style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: '#666',
                    marginBottom: 4
                  }}>
                    {lead.last_message}
                  </div>
                  <div style={{ fontSize: 12, color: '#999' }}>
                    {new Date(lead.last_message_time).toLocaleString('zh-CN')}
                  </div>
                </div>
              }
            />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: isHighIntent ? '#ff4d4f' : '#1890ff' }}>
                {Math.round(lead.intent_score * 100)}
              </div>
              <div style={{ fontSize: 12, color: '#999' }}>意向分</div>
            </div>
          </List.Item>
        );
      }}
    />
  );
}
