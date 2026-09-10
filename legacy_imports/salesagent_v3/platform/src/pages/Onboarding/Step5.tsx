import { useState } from 'react';
import { Card, Button, Result } from 'antd';
import { CheckCircleOutlined, RocketOutlined } from '@ant-design/icons';
import { onboardingApi } from '../../services/api';

interface Step5Props {
  userId: string;
  onComplete: () => void;
}

export default function Step5Activate({ userId, onComplete }: Step5Props) {
  const [loading, setLoading] = useState(false);
  const [activated, setActivated] = useState(false);

  const handleActivate = async () => {
    setLoading(true);
    try {
      await onboardingApi.activate(userId);
      setActivated(true);
    } catch (error) {
      console.error('Activation error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (activated) {
    return (
      <Card style={{ maxWidth: 600, margin: '0 auto' }}>
        <Result
          status="success"
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title="账户激活成功！"
          subTitle="欢迎使用 SalesBoost AI 销售助手"
          extra={[
            <Button
              key="start"
              type="primary"
              size="large"
              icon={<RocketOutlined />}
              onClick={onComplete}
            >
              开始使用
            </Button>
          ]}
        />

        <div style={{
          marginTop: 32,
          padding: 24,
          background: '#f0f2f5',
          borderRadius: 8
        }}>
          <h4 style={{ marginBottom: 16 }}>🎉 您已完成所有设置！</h4>
          <ul style={{ margin: 0, paddingLeft: 20, color: '#666' }}>
            <li>AI 已开始学习您的业务知识</li>
            <li>系统将根据您的偏好自动调整沟通风格</li>
            <li>您可以随时在设置中修改配置</li>
            <li>遇到问题可以随时人工接管会话</li>
          </ul>
        </div>

        <div style={{
          marginTop: 24,
          padding: 16,
          background: '#e6f7ff',
          border: '1px solid #91d5ff',
          borderRadius: 8
        }}>
          <h4 style={{ marginBottom: 8, color: '#1890ff' }}>💡 使用建议</h4>
          <ul style={{ margin: 0, paddingLeft: 20, color: '#666', fontSize: 14 }}>
            <li>前 1-2 周建议保持人工接管模式，观察 AI 表现</li>
            <li>定期查看 AI 建议，帮助 AI 学习您的话术风格</li>
            <li>及时反馈 AI 的不当回复，系统会持续优化</li>
            <li>关注每日摘要，了解客户意向变化趋势</li>
          </ul>
        </div>
      </Card>
    );
  }

  return (
    <Card style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
      <h2>步骤 5: 激活账户</h2>
      <p style={{ color: '#666', marginBottom: 32 }}>
        恭喜！您已完成所有配置步骤
      </p>

      <div style={{
        padding: 32,
        background: '#f0f2f5',
        borderRadius: 8,
        marginBottom: 32
      }}>
        <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 16 }} />
        <h3>准备就绪</h3>
        <p style={{ color: '#666' }}>
          点击下方按钮激活您的 AI 销售助手
        </p>
      </div>

      <div style={{
        marginBottom: 32,
        padding: 24,
        background: 'white',
        border: '1px solid #d9d9d9',
        borderRadius: 8,
        textAlign: 'left'
      }}>
        <h4 style={{ marginBottom: 16 }}>✓ 已完成配置：</h4>
        <ul style={{ margin: 0, paddingLeft: 20, color: '#666' }}>
          <li>企业微信绑定</li>
          <li>知识库文档上传</li>
          <li>AI 偏好设置</li>
          <li>沙盒环境测试</li>
        </ul>
      </div>

      <Button
        type="primary"
        size="large"
        icon={<RocketOutlined />}
        loading={loading}
        onClick={handleActivate}
        style={{ height: 48, fontSize: 16, paddingLeft: 32, paddingRight: 32 }}
      >
        激活账户
      </Button>

      <p style={{ marginTop: 16, color: '#999', fontSize: 12 }}>
        激活后，AI 将开始处理您的客户对话
      </p>
    </Card>
  );
}
