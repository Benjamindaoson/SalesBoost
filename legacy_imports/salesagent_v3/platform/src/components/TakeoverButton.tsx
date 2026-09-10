import { useState } from 'react';
import { Button, message } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { sessionsApi } from '../services/api';

interface TakeoverButtonProps {
  sessionId: string;
  aiDriving: boolean;
  onStatusChange?: (aiDriving: boolean) => void;
}

export default function TakeoverButton({
  sessionId,
  aiDriving,
  onStatusChange
}: TakeoverButtonProps) {
  const [loading, setLoading] = useState(false);
  const [isAiDriving, setIsAiDriving] = useState(aiDriving);

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (isAiDriving) {
        // Takeover
        await sessionsApi.takeoverSession(sessionId);
        setIsAiDriving(false);
        message.success('已接管会话，AI 已暂停');
        onStatusChange?.(false);
      } else {
        // Resume AI
        await sessionsApi.resumeAI(sessionId);
        setIsAiDriving(true);
        message.success('已恢复 AI 主驾');
        onStatusChange?.(true);
      }
    } catch (error) {
      message.error('操作失败，请重试');
      console.error('Takeover toggle error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      type={isAiDriving ? 'default' : 'primary'}
      icon={isAiDriving ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
      loading={loading}
      onClick={handleToggle}
      size="large"
    >
      {isAiDriving ? 'AI 主驾中 - 点击接管' : '人工控制中 - 恢复 AI'}
    </Button>
  );
}
