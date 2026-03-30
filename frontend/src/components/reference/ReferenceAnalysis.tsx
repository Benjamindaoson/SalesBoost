import React, { useState, useEffect } from 'react';
import { BarChart, TrendingUp, AlertCircle, CheckCircle, FileText, Brain } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

interface AnalysisData {
  id: number;
  reference_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  summary?: string;
  key_topics?: string[];
  sentiment?: {
    score: number;
    label: string;
  };
  readability?: {
    score: number;
    grade_level: string;
  };
  statistics?: {
    word_count: number;
    sentence_count: number;
    paragraph_count: number;
    avg_sentence_length: number;
  };
  entities?: Array<{
    text: string;
    type: string;
    count: number;
  }>;
  insights?: string[];
  recommendations?: string[];
}

interface ReferenceAnalysisProps {
  referenceId: number;
  referenceName?: string;
}

export const ReferenceAnalysis: React.FC<ReferenceAnalysisProps> = ({
  referenceId,
  referenceName,
}) => {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysis();
  }, [referenceId]);

  const fetchAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`/api/v1/references/${referenceId}/analysis`);
      setAnalysis(response.data);
    } catch (err: any) {
      console.error('Failed to fetch analysis:', err);
      setError(err.response?.data?.message || 'Failed to load analysis');
      toast.error('Failed to load analysis');
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalysis = async () => {
    try {
      setLoading(true);
      await axios.post(`/api/v1/references/${referenceId}/analyze`);
      toast.success('Analysis started');
      setTimeout(fetchAnalysis, 2000);
    } catch (err: any) {
      console.error('Failed to trigger analysis:', err);
      toast.error('Failed to start analysis');
      setLoading(false);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score >= 0.5) return 'text-green-600';
    if (score >= 0) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getReadabilityColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center flex-col space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <p className="text-gray-600">{error}</p>
          <button
            onClick={triggerAnalysis}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Start Analysis
          </button>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center flex-col space-y-4">
          <Brain className="h-12 w-12 text-gray-400" />
          <p className="text-gray-600">No analysis available</p>
          <button
            onClick={triggerAnalysis}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Start Analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Content Analysis</h2>
              {referenceName && (
                <p className="text-sm text-gray-500 mt-1">{referenceName}</p>
              )}
            </div>
            <span
              className={`px-3 py-1 text-xs font-semibold rounded-full ${
                analysis.status === 'completed'
                  ? 'bg-green-100 text-green-800'
                  : analysis.status === 'processing'
                  ? 'bg-yellow-100 text-yellow-800'
                  : analysis.status === 'failed'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {analysis.status}
            </span>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {analysis.summary && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2 flex items-center">
                <FileText className="h-4 w-4 mr-2" />
                Summary
              </h3>
              <p className="text-sm text-gray-700 leading-relaxed">{analysis.summary}</p>
            </div>
          )}

          {analysis.statistics && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <BarChart className="h-4 w-4 mr-2" />
                Statistics
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Words</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {analysis.statistics.word_count.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Sentences</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {analysis.statistics.sentence_count.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Paragraphs</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {analysis.statistics.paragraph_count.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Avg Sentence</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {analysis.statistics.avg_sentence_length.toFixed(1)} words
                  </p>
                </div>
              </div>
            </div>
          )}

          {analysis.sentiment && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Sentiment Analysis</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Overall Sentiment</span>
                  <span
                    className={`text-sm font-semibold ${getSentimentColor(
                      analysis.sentiment.score
                    )}`}
                  >
                    {analysis.sentiment.label}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      analysis.sentiment.score >= 0.5
                        ? 'bg-green-500'
                        : analysis.sentiment.score >= 0
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{
                      width: `${((analysis.sentiment.score + 1) / 2) * 100}%`,
                    }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          {analysis.readability && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Readability</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Readability Score</span>
                  <span
                    className={`text-sm font-semibold ${getReadabilityColor(
                      analysis.readability.score
                    )}`}
                  >
                    {analysis.readability.score}/100
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full ${
                      analysis.readability.score >= 80
                        ? 'bg-green-500'
                        : analysis.readability.score >= 60
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${analysis.readability.score}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-600">
                  Grade Level: {analysis.readability.grade_level}
                </p>
              </div>
            </div>
          )}

          {analysis.key_topics && analysis.key_topics.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Key Topics</h3>
              <div className="flex flex-wrap gap-2">
                {analysis.key_topics.map((topic, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.entities && analysis.entities.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Named Entities</h3>
              <div className="space-y-2">
                {analysis.entities.slice(0, 10).map((entity, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded"
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">{entity.text}</span>
                      <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-200 rounded">
                        {entity.type}
                      </span>
                    </div>
                    <span className="text-xs text-gray-600">{entity.count}x</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.insights && analysis.insights.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <TrendingUp className="h-4 w-4 mr-2" />
                Insights
              </h3>
              <ul className="space-y-2">
                {analysis.insights.map((insight, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircle className="h-4 w-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700">{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <AlertCircle className="h-4 w-4 mr-2" />
                Recommendations
              </h3>
              <ul className="space-y-2">
                {analysis.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-blue-500 mr-2 flex-shrink-0">→</span>
                    <span className="text-sm text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
