/**
 * Knowledge Base Management Page
 *
 * Main page for managing the knowledge base.
 * Integrates:
 * - KnowledgeUploader for adding new content
 * - KnowledgeTable for viewing and managing entries
 * - KnowledgeStats for analytics and insights
 */

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import KnowledgeUploader from '@/components/knowledge/KnowledgeUploader';
import KnowledgeTable from '@/components/knowledge/KnowledgeTable';
import KnowledgeStats from '@/components/knowledge/KnowledgeStats';
import { Database, Upload, BarChart3, Bot, Send, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { llmService, ChatMessage } from '@/services/llm.service';

export default function KnowledgeBase() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState('browse');
  
  // Test Tab State
  const [testContext, setTestContext] = useState('SalesBoost is a leading AI-powered sales training platform. It helps sales teams improve their skills through realistic role-play scenarios. The platform features an AI Coach that provides real-time feedback.');
  const [testQuestion, setTestQuestion] = useState('');
  const [testAnswer, setTestAnswer] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  const handleUploadSuccess = () => {
    // Trigger refresh of table and stats
    setRefreshTrigger(prev => prev + 1);
    // Switch to browse tab to see the uploaded content
    setActiveTab('browse');
  };

  const handleTestQA = async () => {
    if (!testQuestion.trim() || !testContext.trim()) return;
    
    setIsTesting(true);
    try {
      const systemPrompt = llmService.createKnowledgeBasePrompt(testContext);
      const messages: ChatMessage[] = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Context: ${testContext}\n\nQuestion: ${testQuestion}` }
      ];

      const response = await llmService.chatCompletion(messages);
      setTestAnswer(response);
    } catch (error) {
      console.error("QA Error:", error);
      setTestAnswer("Error: Could not retrieve answer from AI.");
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-600 mt-1">
            Manage your sales knowledge, documents, and training materials
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Database className="w-5 h-5" />
          <span>Vector Database: Qdrant</span>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
          <TabsTrigger value="browse" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            <span className="hidden sm:inline">Browse</span>
          </TabsTrigger>
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            <span className="hidden sm:inline">Upload</span>
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Analytics</span>
          </TabsTrigger>
          <TabsTrigger value="test" className="flex items-center gap-2">
            <Bot className="w-4 h-4" />
            <span className="hidden sm:inline">Test AI</span>
          </TabsTrigger>
        </TabsList>

        {/* Browse Tab */}
        <TabsContent value="browse" className="mt-6">
          <KnowledgeTable refreshTrigger={refreshTrigger} />
        </TabsContent>

        {/* Upload Tab */}
        <TabsContent value="upload" className="mt-6">
          <div className="max-w-3xl mx-auto">
            <KnowledgeUploader onUploadSuccess={handleUploadSuccess} />
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="mt-6">
          <KnowledgeStats refreshTrigger={refreshTrigger} />
        </TabsContent>

        {/* Test AI Tab */}
        <TabsContent value="test" className="mt-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Knowledge Context</CardTitle>
                <CardDescription>Paste text here to simulate a document retrieval.</CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea 
                  value={testContext}
                  onChange={(e) => setTestContext(e.target.value)}
                  className="min-h-[300px] font-mono text-sm"
                  placeholder="Paste your knowledge text here..."
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Ask Question</CardTitle>
                <CardDescription>Test how the AI answers based on the context.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input 
                    value={testQuestion}
                    onChange={(e) => setTestQuestion(e.target.value)}
                    placeholder="Ask a question..."
                    onKeyDown={(e) => e.key === 'Enter' && handleTestQA()}
                  />
                  <Button onClick={handleTestQA} disabled={isTesting || !testQuestion.trim()}>
                    {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
                
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-gray-500 mb-2">AI Answer:</h4>
                  <div className="bg-gray-50 rounded-lg p-4 min-h-[150px] text-sm leading-relaxed border border-gray-100">
                    {testAnswer || <span className="text-gray-400 italic">Answer will appear here...</span>}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Help Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">💡 Knowledge Base Tips</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Upload documents in TXT, MD, PDF, DOC, or DOCX format (max 10MB)</li>
          <li>• Use descriptive sources to organize your knowledge (e.g., "product-docs", "sales-playbook")</li>
          <li>• Assign appropriate sales stages to help the AI provide context-aware coaching</li>
          <li>• The system uses BGE-Reranker for high-quality semantic search</li>
          <li>• All content is automatically vectorized and indexed for fast retrieval</li>
        </ul>
      </div>
    </div>
  );
}
