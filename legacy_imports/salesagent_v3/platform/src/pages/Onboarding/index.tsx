import { useState } from 'react';
import { Steps, Card } from 'antd';
import Step1WeChatBinding from './Step1';
import Step2KnowledgeUpload from './Step2';
import Step3Preferences from './Step3';
import Step4SandboxTest from './Step4';
import Step5Activate from './Step5';

export default function OnboardingFlow() {
  const [currentStep, setCurrentStep] = useState(0);
  const userId = 'user_001'; // TODO: Get from auth context

  const steps = [
    {
      title: '微信绑定',
      content: (
        <Step1WeChatBinding
          userId={userId}
          onComplete={() => setCurrentStep(1)}
        />
      )
    },
    {
      title: '上传文档',
      content: (
        <Step2KnowledgeUpload
          userId={userId}
          onComplete={() => setCurrentStep(2)}
        />
      )
    },
    {
      title: '偏好设置',
      content: (
        <Step3Preferences
          userId={userId}
          onComplete={() => setCurrentStep(3)}
        />
      )
    },
    {
      title: '沙盒测试',
      content: (
        <Step4SandboxTest
          onComplete={() => setCurrentStep(4)}
        />
      )
    },
    {
      title: '激活账户',
      content: (
        <Step5Activate
          userId={userId}
          onComplete={() => {
            // Navigate to dashboard
            window.location.href = '/dashboard';
          }}
        />
      )
    }
  ];

  return (
    <div style={{ padding: '40px 20px', maxWidth: 1200, margin: '0 auto' }}>
      <Card style={{ marginBottom: 32 }}>
        <h1 style={{ textAlign: 'center', marginBottom: 32 }}>
          欢迎使用 SalesBoost AI 销售助手
        </h1>
        <Steps
          current={currentStep}
          items={steps.map(step => ({ title: step.title }))}
        />
      </Card>

      <div style={{ marginTop: 32 }}>
        {steps[currentStep].content}
      </div>
    </div>
  );
}
