import { useState } from 'react';
import { Layout, Row, Col } from 'antd';
import DailySummary from '../components/DailySummary';
import LeadList from '../components/LeadList';
import ChatView from '../components/ChatView';
import TakeoverButton from '../components/TakeoverButton';
import AISuggestion from '../components/AISuggestion';

const { Header, Content } = Layout;

export default function Dashboard() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [aiDriving, setAiDriving] = useState(true);
  const [showSuggestion, setShowSuggestion] = useState(false);

  const handleSelectLead = (sessionId: string) => {
    setSelectedSessionId(sessionId);
  };

  const handleStatusChange = (newAiDriving: boolean) => {
    setAiDriving(newAiDriving);
    setShowSuggestion(!newAiDriving); // Show suggestion when taking over
  };

  const handleAdoptSuggestion = (suggestion: string) => {
    // TODO: Insert suggestion into chat input
    console.log('Adopted suggestion:', suggestion);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <h1 style={{ margin: 0, lineHeight: '64px' }}>SalesBoost AI 销售助手</h1>
      </Header>

      <Content style={{ padding: '24px' }}>
        {/* Daily Summary */}
        <div style={{ marginBottom: 24 }}>
          <DailySummary />
        </div>

        {/* Main Content */}
        <Row gutter={16}>
          {/* Lead List */}
          <Col span={6}>
            <div style={{ background: '#fff', borderRadius: 8, height: 'calc(100vh - 280px)' }}>
              <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
                <h3 style={{ margin: 0 }}>活跃会话</h3>
              </div>
              <div style={{ height: 'calc(100% - 57px)', overflowY: 'auto' }}>
                <LeadList
                  onSelectLead={handleSelectLead}
                  selectedSessionId={selectedSessionId || undefined}
                />
              </div>
            </div>
          </Col>

          {/* Chat View */}
          <Col span={18}>
            {selectedSessionId ? (
              <div>
                {/* Takeover Button */}
                <div style={{ marginBottom: 16, textAlign: 'right' }}>
                  <TakeoverButton
                    sessionId={selectedSessionId}
                    aiDriving={aiDriving}
                    onStatusChange={handleStatusChange}
                  />
                </div>

                {/* Chat */}
                <div style={{ height: 'calc(100vh - 320px)' }}>
                  <ChatView
                    sessionId={selectedSessionId}
                    aiDriving={aiDriving}
                  />
                </div>
              </div>
            ) : (
              <div style={{
                background: '#fff',
                borderRadius: 8,
                height: 'calc(100vh - 280px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 16 }}>请从左侧选择一个会话</p>
                </div>
              </div>
            )}
          </Col>
        </Row>

        {/* AI Suggestion */}
        {selectedSessionId && (
          <AISuggestion
            sessionId={selectedSessionId}
            visible={showSuggestion}
            onAdopt={handleAdoptSuggestion}
          />
        )}
      </Content>
    </Layout>
  );
}
