import React, { useState } from 'react';
import { Download, X, FileText, FileJson, File } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  exportType: 'session' | 'project' | 'analytics';
  itemId?: number;
  itemName?: string;
}

type ExportFormat = 'json' | 'markdown' | 'pdf' | 'csv';

export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  exportType,
  itemId,
  itemName,
}) => {
  const [format, setFormat] = useState<ExportFormat>('json');
  const [includeMessages, setIncludeMessages] = useState(true);
  const [includeEvaluation, setIncludeEvaluation] = useState(true);
  const [includeSessions, setIncludeSessions] = useState(true);
  const [loading, setLoading] = useState(false);

  const getAvailableFormats = (): ExportFormat[] => {
    if (exportType === 'analytics') {
      return ['json', 'markdown', 'csv'];
    }
    return ['json', 'markdown', 'pdf'];
  };

  const getFormatIcon = (fmt: ExportFormat) => {
    switch (fmt) {
      case 'json':
        return <FileJson className="h-5 w-5" />;
      case 'markdown':
        return <FileText className="h-5 w-5" />;
      case 'pdf':
        return <File className="h-5 w-5" />;
      case 'csv':
        return <FileText className="h-5 w-5" />;
      default:
        return <File className="h-5 w-5" />;
    }
  };

  const getFormatDescription = (fmt: ExportFormat) => {
    switch (fmt) {
      case 'json':
        return 'Machine-readable format, ideal for data processing';
      case 'markdown':
        return 'Human-readable format, great for documentation';
      case 'pdf':
        return 'Professional format, perfect for reports';
      case 'csv':
        return 'Spreadsheet format, ideal for data analysis';
      default:
        return '';
    }
  };

  const handleExport = async () => {
    try {
      setLoading(true);

      let url = '';
      let params: any = { format };

      if (exportType === 'session' && itemId) {
        url = `/api/v1/export/sessions/${itemId}/export`;
        params.include_messages = includeMessages;
        params.include_evaluation = includeEvaluation;
      } else if (exportType === 'project' && itemId) {
        url = `/api/v1/export/projects/${itemId}/export`;
        params.include_sessions = includeSessions;
      } else if (exportType === 'analytics') {
        url = '/api/v1/export/analytics/export';
      } else {
        throw new Error('Invalid export configuration');
      }

      const response = await axios.get(url, {
        params,
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;

      // Determine filename
      const contentDisposition = response.headers['content-disposition'];
      let filename = `export.${format}`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      } else if (itemName) {
        filename = `${itemName.replace(/\s+/g, '_')}.${format}`;
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      toast.success('Export completed successfully');
      onClose();
    } catch (error: any) {
      console.error('Export failed:', error);
      toast.error(error.response?.data?.message || 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const availableFormats = getAvailableFormats();

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen">&#8203;</span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <Download className="h-6 w-6 text-blue-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">Export Data</h3>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500"
                disabled={loading}
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            {itemName && (
              <p className="text-sm text-gray-600 mb-4">
                Exporting: <span className="font-medium">{itemName}</span>
              </p>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Export Format
                </label>
                <div className="space-y-2">
                  {availableFormats.map((fmt) => (
                    <label
                      key={fmt}
                      className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                        format === fmt
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <input
                        type="radio"
                        name="format"
                        value={fmt}
                        checked={format === fmt}
                        onChange={(e) => setFormat(e.target.value as ExportFormat)}
                        className="mt-1"
                        disabled={loading}
                      />
                      <div className="ml-3 flex-1">
                        <div className="flex items-center">
                          {getFormatIcon(fmt)}
                          <span className="ml-2 text-sm font-medium text-gray-900 uppercase">
                            {fmt}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {getFormatDescription(fmt)}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {exportType === 'session' && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Options</label>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={includeMessages}
                        onChange={(e) => setIncludeMessages(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        disabled={loading}
                      />
                      <span className="ml-2 text-sm text-gray-700">
                        Include conversation messages
                      </span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={includeEvaluation}
                        onChange={(e) => setIncludeEvaluation(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        disabled={loading}
                      />
                      <span className="ml-2 text-sm text-gray-700">
                        Include evaluation data
                      </span>
                    </label>
                  </div>
                </div>
              )}

              {exportType === 'project' && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Options</label>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={includeSessions}
                        onChange={(e) => setIncludeSessions(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        disabled={loading}
                      />
                      <span className="ml-2 text-sm text-gray-700">Include session data</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={handleExport}
              disabled={loading}
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
