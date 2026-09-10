import { useQuery } from '@tanstack/react-query';
import { Card, Col, Row, Statistic, Spin } from 'antd';
import {
  MessageOutlined,
  FireOutlined,
  TrophyOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { analyticsApi } from '../services/api';

export default function DailySummary() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dailySummary'],
    queryFn: async () => {
      const response = await analyticsApi.getDailySummary();
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <p style={{ color: 'red' }}>加载数据失败</p>
      </Card>
    );
  }

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日跟进"
            value={data?.today_followups || 0}
            prefix={<MessageOutlined />}
            suffix="次"
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="高意向客户"
            value={data?.high_intent_count || 0}
            prefix={<FireOutlined style={{ color: '#ff4d4f' }} />}
            suffix="位"
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日成单"
            value={data?.deals_closed || 0}
            prefix={<TrophyOutlined style={{ color: '#52c41a' }} />}
            suffix="单"
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="平均响应时间"
            value={data?.avg_response_time || 0}
            prefix={<ClockCircleOutlined />}
            suffix="秒"
            precision={1}
          />
        </Card>
      </Col>
    </Row>
  );
}
