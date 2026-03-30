import React, { useState, useEffect } from 'react';
import { FileText, Download, Trash2, Eye, Search, Filter } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

interface Reference {
  id: number;
  name: string;
  file_type: string;
  file_size: number;
  upload_date: string;
  status: 'processing' | 'ready' | 'error';
  project_id?: number;
  url?: string;
  analysis_status?: string;
  metadata?: {
    pages?: number;
    word_count?: number;
    language?: string;
  };
}

interface ReferenceListProps {
  projectId?: number;
  onViewAnalysis?: (reference: Reference) => void;
}

export const ReferenceList: React.FC<ReferenceListProps> = ({
  projectId,
  onViewAnalysis,
}) => {
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    fetchReferences();
  }, [projectId]);

  const fetchReferences = async () => {
    try {
      setLoading(true);
      const params = projectId ? { project_id: projectId } : {};
      const response = await axios.get('/api/v1/references', { params });
      setReferences(response.data);
    } catch (error) {
      console.error('Failed to fetch references:', error);
      toast.error('Failed to load references');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this reference?')) return;

    try {
      await axios.delete(`/api/v1/references/${id}`);
      toast.success('Reference deleted successfully');
      fetchReferences();
    } catch (error) {
      console.error('Failed to delete reference:', error);
      toast.error('Failed to delete reference');
    }
  };

  const handleDownload = async (reference: Reference) => {
    try {
      const response = await axios.get(`/api/v1/references/${reference.id}/download`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', reference.name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('Download started');
    } catch (error) {
      console.error('Failed to download reference:', error);
      toast.error('Failed to download reference');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('text')) return '📃';
    return '📎';
  };

  const filteredReferences = references.filter((ref) => {
    const matchesSearch = ref.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || ref.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
          <h2 className="text-xl font-semibold text-gray-900">Reference Materials</h2>

          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search references..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
            </div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="all">All Status</option>
              <option value="ready">Ready</option>
              <option value="processing">Processing</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-200">
        {filteredReferences.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            {searchTerm || filterStatus !== 'all'
              ? 'No references match your filters'
              : 'No references uploaded yet'}
          </div>
        ) : (
          filteredReferences.map((reference) => (
            <div
              key={reference.id}
              className="px-6 py-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start flex-1 min-w-0">
                  <span className="text-3xl mr-4">{getFileIcon(reference.file_type)}</span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {reference.name}
                      </h3>
                      <span
                        className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStatusColor(
                          reference.status
                        )}`}
                      >
                        {reference.status}
                      </span>
                    </div>

                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>{formatFileSize(reference.file_size)}</span>
                      <span>•</span>
                      <span>{new Date(reference.upload_date).toLocaleDateString()}</span>
                      {reference.metadata?.pages && (
                        <>
                          <span>•</span>
                          <span>{reference.metadata.pages} pages</span>
                        </>
                      )}
                      {reference.metadata?.word_count && (
                        <>
                          <span>•</span>
                          <span>{reference.metadata.word_count.toLocaleString()} words</span>
                        </>
                      )}
                    </div>

                    {reference.analysis_status && (
                      <div className="mt-2">
                        <span className="text-xs text-blue-600">
                          Analysis: {reference.analysis_status}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {reference.status === 'ready' && onViewAnalysis && (
                    <button
                      onClick={() => onViewAnalysis(reference)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-md"
                      title="View Analysis"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  )}

                  <button
                    onClick={() => handleDownload(reference)}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </button>

                  <button
                    onClick={() => handleDelete(reference.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-md"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
