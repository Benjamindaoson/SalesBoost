import { useState } from 'react';
import { Card, QRCode, Spin, message } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { onboardingApi } from '../../services/api';

interface Step1Props {
  userId: string;
  onComplete: () => void;
}

export default function Step1WeChatBinding({ userId, onComplete }: Step1Props) {
  const [qrUrl, setQrUrl] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [bound, setBound] = useState(false);

  const generateQR = async () => {
    setLoading(true);
    try {
      const response = await onboardingApi.getWeChatQR(userId);
      setQrUrl(response.data.qr_url);

      // Poll for binding status
      const checkInterval = setInterval(async () => {
        try {
          const status = await onboardingApi.getStatus(userId);
          if (status.data.steps.wechat_binding) {
            setBound(true);
            clearInterval(checkInterval);
            message.success('微信绑定成功！');
            setTimeout(onComplete, 1500);
          }
        } catch (error) {
          console.error('Failed to check binding status:', error);
        }
      }, 2000);

      // Clear interval after 5 minutes
      setTimeout(() => clearInterval(checkInterval), 300000);
    } catch (error) {
      message.error('生成二维码失败');
      console.error('Failed to generate QR code:', error);
    } finally {
      setLoading(false);
    }
  };

  useState(() => {
    generateQR();
  });

  return (
    <Card style={{ textAlign: 'center', maxWidth: 500, margin: '0 auto' }}>
      <h2>步骤 1: 绑定企业微信</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>
        使用企业微信扫描下方二维码完成绑定
      </p>

      {loading ? (
        <Spin size="large" />
      ) : bound ? (
        <div>
          <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 16 }} />
          <p style={{ fontSize: 18, color: '#52c41a' }}>绑定成功！</p>
        </div>
      ) : qrUrl ? (
        <div>
          <QRCode value={qrUrl} size={256} />
          <p style={{ marginTop: 16, color: '#999', fontSize: 12 }}>
            二维码 5 分钟内有效
          </p>
        </div>
      ) : null}
    </Card>
  );
}
