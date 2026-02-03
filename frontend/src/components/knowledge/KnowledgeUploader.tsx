/**
 * Knowledge Uploader Component
 *
 * Provides drag-and-drop file upload and text input for knowledge base content.
 * Features:
 * - Drag and drop file upload
 * - Text content input
 * - Metadata form (source, stage, version)
 * - Progress indicator
 * - Success/error notifications
 */

import { useState, useCallback } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import knowledgeService, { type KnowledgeMetadata, type UploadProgress } from '@/services/knowledge.service';

interface KnowledgeUploaderProps {
  onUploadSuccess?: () => void;
}

export default function KnowledgeUploader({ onUploadSuccess }: KnowledgeUploaderProps) {
  const [uploadMode, setUploadMode] = useState<'file' | 'text'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState('');
  const [metadata, setMetadata] = useState<KnowledgeMetadata>({
    source: '',
    stage: 'discovery',
    version: '1.0',
  });
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validation = knowledgeService.validateFile(file);
      if (validation.valid) {
        setSelectedFile(file);
      } else {
        toast.error(validation.error);
      }
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validation = knowledgeService.validateFile(file);
      if (validation.valid) {
        setSelectedFile(file);
      } else {
        toast.error(validation.error);
      }
    }
  };

  const handleUpload = async () => {
    if (uploadMode === 'file' && !selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }

    if (uploadMode === 'text' && !textContent.trim()) {
      toast.error('Please enter some text content');
      return;
    }

    if (!metadata.source) {
      toast.error('Please specify a source');
      return;
    }

    setUploading(true);
    setUploadProgress(null);

    try {
      if (uploadMode === 'file' && selectedFile) {
        const result = await knowledgeService.uploadFile(
          selectedFile,
          metadata,
          (progress) => setUploadProgress(progress)
        );
        toast.success(result.message || 'File uploaded successfully');
      } else if (uploadMode === 'text') {
        const result = await knowledgeService.uploadText(textContent, metadata);
        toast.success(result.message || 'Text uploaded successfully');
      }

      // Reset form
      setSelectedFile(null);
      setTextContent('');
      setMetadata({ source: '', stage: 'discovery', version: '1.0' });
      setUploadProgress(null);

      // Notify parent
      onUploadSuccess?.();
    } catch (error: any) {
      console.error('Upload failed:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Knowledge</h3>

      {/* Upload Mode Toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setUploadMode('file')}
          className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors ${
            uploadMode === 'file'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Upload className="w-4 h-4 inline mr-2" />
          Upload File
        </button>
        <button
          onClick={() => setUploadMode('text')}
          className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors ${
            uploadMode === 'text'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <FileText className="w-4 h-4 inline mr-2" />
          Enter Text
        </button>
      </div>

      {/* File Upload Mode */}
      {uploadMode === 'file' && (
        <div className="mb-6">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-indigo-500 bg-indigo-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {selectedFile ? (
              <div className="flex items-center justify-between bg-gray-50 p-4 rounded">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-indigo-600" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">
                  Drag and drop your file here, or click to browse
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Supported: TXT, MD, PDF, DOC, DOCX (Max 10MB)
                </p>
                <label className="inline-block">
                  <input
                    type="file"
                    onChange={handleFileSelect}
                    accept=".txt,.md,.pdf,.doc,.docx"
                    className="hidden"
                  />
                  <span className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 cursor-pointer">
                    Browse Files
                  </span>
                </label>
              </>
            )}
          </div>
        </div>
      )}

      {/* Text Input Mode */}
      {uploadMode === 'text' && (
        <div className="mb-6">
          <textarea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            placeholder="Enter your knowledge content here..."
            className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
          <p className="text-sm text-gray-500 mt-2">
            {textContent.length} characters
          </p>
        </div>
      )}

      {/* Metadata Form */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Source <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={metadata.source}
            onChange={(e) => setMetadata({ ...metadata, source: e.target.value })}
            placeholder="e.g., product-docs, sales-playbook"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Sales Stage
          </label>
          <select
            value={metadata.stage}
            onChange={(e) => setMetadata({ ...metadata, stage: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="discovery">Discovery</option>
            <option value="qualification">Qualification</option>
            <option value="proposal">Proposal</option>
            <option value="negotiation">Negotiation</option>
            <option value="closing">Closing</option>
            <option value="general">General</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Version
          </label>
          <input
            type="text"
            value={metadata.version}
            onChange={(e) => setMetadata({ ...metadata, version: e.target.value })}
            placeholder="e.g., 1.0, 2.1"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Upload Progress */}
      {uploading && uploadProgress && (
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Uploading...</span>
            <span>{uploadProgress.percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={uploading || (uploadMode === 'file' && !selectedFile) || (uploadMode === 'text' && !textContent.trim())}
        className="w-full py-3 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        {uploading ? 'Uploading...' : 'Upload Knowledge'}
      </button>
    </div>
  );
}
