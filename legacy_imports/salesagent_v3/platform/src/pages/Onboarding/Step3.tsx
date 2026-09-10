import { useState } from 'react';
import { Card, Form, Radio, Slider, Switch, Button, message } from 'antd';
import { onboardingApi } from '../../services/api';
import type { UserPreferences } from '../../types';

interface Step3Props {
  userId: string;
  onComplete: () => void;
}

export default function Step3Preferences({ userId, onComplete }: Step3Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: UserPreferences) => {
    setLoading(true);
    try {
      await onboardingApi.setPreferences(userId, values);
      message.success('偏好设置已保存！');
      setTimeout(onComplete, 1000);
    } catch (error) {
      message.error('保存失败，请重试');
      console.error('Failed to save preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2>步骤 3: 设置 AI 偏好</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>
        根据您的业务特点，调整 AI 的沟通风格和行为
      </p>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          tone: 'professional',
          response_speed: 30,
          auto_send: true
        }}
      >
        <Form.Item
          label="沟通语气"
          name="tone"
          rules={[{ required: true, message: '请选择沟通语气' }]}
        >
          <Radio.Group>
            <Radio.Button value="professional">专业正式</Radio.Button>
            <Radio.Button value="friendly">亲切友好</Radio.Button>
            <Radio.Button value="concise">简洁高效</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          label="响应速度（秒）"
          name="response_speed"
          tooltip="AI 回复的延迟时间，模拟真人打字节奏"
        >
          <Slider
            min={15}
            max={90}
            marks={{
              15: '快速 (15s)',
              30: '适中 (30s)',
              60: '稳重 (60s)',
              90: '缓慢 (90s)'
            }}
          />
        </Form.Item>

        <Form.Item
          label="自动发送"
          name="auto_send"
          valuePropName="checked"
          tooltip="开启后，AI 生成的消息将自动发送；关闭后需要人工审核"
        >
          <Switch
            checkedChildren="开启"
            unCheckedChildren="关闭"
          />
        </Form.Item>

        <Form.Item style={{ marginTop: 32 }}>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            size="large"
            block
          >
            保存设置
          </Button>
        </Form.Item>
      </Form>

      <div style={{
        marginTop: 24,
        padding: 16,
        background: '#f0f2f5',
        borderRadius: 8
      }}>
        <h4 style={{ marginBottom: 8 }}>💡 建议</h4>
        <ul style={{ margin: 0, paddingLeft: 20, color: '#666', fontSize: 14 }}>
          <li>金融保险行业建议使用"专业正式"语气</li>
          <li>教育培训行业建议使用"亲切友好"语气</li>
          <li>响应速度建议设置在 30-60 秒之间</li>
          <li>初次使用建议关闭"自动发送"，熟悉后再开启</li>
        </ul>
      </div>
    </Card>
  );
}
