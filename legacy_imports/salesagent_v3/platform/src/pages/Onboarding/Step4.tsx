import { useState } from 'react';
import { Card, Button, Input, Space, Divider, Tag, message } from 'antd';
import { SendOutlined, RobotOutlined } from '@ant-design/icons';
import { onboardingApi } from '../../services/api';

interface Step4Props {
  onComplete: () => void;
}

const TEST_SCENARIOS = [
  {
    title: '场景 1: 初次咨询',
    message: '你好，我想了解一下你们的保险产品'
  },
  {
    title: '场景 2: 价格询问',
    message: '这个保险多少钱？有什么优惠吗？'
  },
  {
    title: '场景 3: 犹豫不决',
    message: '我再考虑考虑吧，过几天再说'
  }
];

export default function Step4SandboxTest({ onComplete }: Step4Props) {
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<{
    response: string;
    intent: string;
    tactics: any;
  } | null>(null);
  const [testedCount, setTestedCount] = useState(0);

  const handleTest = async (testMessage: string) => {
    setLoading(true);
    setResponse(null);

    try {
      const result = await onboardingApi.testChat(testMessage);
      setResponse(result.data);
      setTestedCount((prev) => prev + 1);
      message.success('测试成功！');
    } catch (error) {
      message.error('测试失败，请重试');
      console.error('Sandbox test error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomTest = () => {
    if (!inputValue.trim()) {
      message.warning('请输入测试消息');
      return;
    }
    handleTest(inputValue);
    setInputValue('');
  };

  return (
    <Card style={{ maxWidth: 700, margin: '0 auto' }}>
      <h2>步骤 4: 沙盒测试</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>
        在安全的沙盒环境中测试 AI 的响应效果，不会影响真实客户
      </p>

      {/* Quick test scenarios */}
      <div style={{ marginBottom: 24 }}>
        <h4>快速测试场景：</h4>
        <Space direction="vertical" style={{ width: '100%' }}>
          {TEST_SCENARIOS.map((scenario, index) => (
            <Button
              key={index}
              block
              onClick={() => handleTest(scenario.message)}
              loading={loading}
            >
              {scenario.title}
            </Button>
          ))}
        </Space>
      </div>

      <Divider>或</Divider>

      {/* Custom test */}
      <div style={{ marginBottom: 24 }}>
        <h4>自定义测试：</h4>
        <Input.Search
          placeholder="输入测试消息..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onSearch={handleCustomTest}
          enterButton={
            <Button type="primary" icon={<SendOutlined />} loading={loading}>
              测试
            </Button>
          }
          size="large"
        />
      </div>

      {/* Response display */}
      {response && (
        <Card
          style={{ background: '#f0f2f5', marginTop: 24 }}
          title={
            <span>
              <RobotOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              AI 响应结果
            </span>
          }
        >
          <div style={{ marginBottom: 16 }}>
            <strong>AI 回复：</strong>
            <div style={{
              marginTop: 8,
              padding: 12,
              background: 'white',
              borderRadius: 4,
              whiteSpace: 'pre-wrap'
            }}>
              {response.response}
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <strong>意图识别：</strong>
            <div style={{ marginTop: 8 }}>
              <Tag color="blue">{response.intent}</Tag>
            </div>
          </div>

          {response.tactics && (
            <div>
              <strong>策略分析：</strong>
              <div style={{ marginTop: 8 }}>
                <Tag color="green">{response.tactics.primary}</Tag>
                <Tag>{response.tactics.tone}</Tag>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Progress indicator */}
      <div style={{
        marginTop: 32,
        padding: 16,
        background: testedCount >= 2 ? '#f6ffed' : '#fff7e6',
        border: `1px solid ${testedCount >= 2 ? '#b7eb8f' : '#ffd591'}`,
        borderRadius: 8,
        textAlign: 'center'
      }}>
        <p style={{ margin: 0, color: testedCount >= 2 ? '#52c41a' : '#d46b08' }}>
          {testedCount >= 2
            ? '✓ 测试完成！您可以继续下一步'
            : `已测试 ${testedCount} 次，建议至少测试 2 个场景`}
        </p>
      </div>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Space>
          <Button
            type="primary"
            size="large"
            onClick={onComplete}
            disabled={testedCount < 1}
          >
            继续下一步
          </Button>
          <Button type="link" onClick={onComplete}>
            跳过测试
          </Button>
        </Space>
      </div>
    </Card>
  );
}
