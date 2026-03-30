import React, { useState, useRef } from 'react';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

interface ReferenceUploadProps {
  projectId?: number;
  onUploadSuccess?: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
  acceptedTypes?: string[];
}

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  url?: string;
}

export const ReferenceUpload: React.FC<ReferenceUploadProps> = ({
  projectId,
  onUploadSuccess,
  maxFiles = 10,
  maxSizeMB = 50,
  acceptedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
  ],
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      handleFiles(selectedFiles);
    }
  };

  const handleFiles = (selectedFiles: File[]) => {
    if (files.length + selectedFiles.length > maxFiles) {
      toast.error(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const validFiles = selectedFiles.filter((file) => {
      if (!acceptedTypes.includes(file.type)) {
        toast.error(`${file.name}: File type not supported`);
        return false;
      }

      if (file.size > maxSizeMB * 1024 * 1024) {
        toast.error(`${file.name}: File size exceeds ${maxSizeMB}MB`);
        return false;
      }

      return true;
    });

    const newFiles: UploadedFile[] = validFiles.map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    validFiles.forEach((file, index) => {
      const fileEntry = newFiles[index];
      if (fileEntry) uploadFile(file, fileEntry.id);
    });
  };

  const uploadFile = async (file: File, fileId: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (projectId) {
      formData.append('project_id', projectId.toString());
    }

    try {
      const response = await axios.post('/api/v1/references/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;

          setFiles((prev) =>
            prev.map((f) => (f.id === fileId ? { ...f, progress } : f))
          );
        },
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? { ...f, status: 'success', progress: 100, url: response.data.url }
            : f
        )
      );

      toast.success(`${file.name} uploaded successfully`);
    } catch (error: any) {
      console.error('Upload failed:', error);
      const errorMessage = error.response?.data?.message || 'Upload failed';

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId ? { ...f, status: 'error', error: errorMessage } : f
        )
      );

      toast.error(`${file.name}: ${errorMessage}`);
    }
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('text')) return '📃';
    return '📎';
  };

  return (
    <div className="space-y-4">
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />

        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />

        <p className="text-sm text-gray-600 mb-2">
          Drag and drop files here, or click to select files
        </p>

        <button
          onClick={() => fileInputRef.current?.click()}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Select Files
        </button>

        <p className="text-xs text-gray-500 mt-4">
          Supported: PDF, DOC, DOCX, TXT, MD (Max {maxSizeMB}MB per file, {maxFiles} files
          total)
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Files</h4>
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
            >
              <div className="flex items-center flex-1 min-w-0">
                <span className="text-2xl mr-3">{getFileIcon(file.type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>

                  {file.status === 'uploading' && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${file.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {file.status === 'error' && (
                    <p className="text-xs text-red-600 mt-1">{file.error}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center ml-4">
                {file.status === 'success' && (
                  <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                )}
                {file.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                )}
                <button
                  onClick={() => removeFile(file.id)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
