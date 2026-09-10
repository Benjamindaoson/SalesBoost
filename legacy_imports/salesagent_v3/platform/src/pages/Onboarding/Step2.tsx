import { useState } from 'react';
import { Card, Upload, Button, message, List } from 'antd';
import { UploadOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { onboardingApi } from '../../services/api';

interface Step2Props {
  userId: string;
  onComplete: () => void;
}

export default function Step2KnowledgeUpload({ userId, onComplete }: Step2Props) {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    setUploading(true);
    const uploaded: string[] = [];

    try {
      for (const file of fileList) {
        if (file.originFileObj) {
          await onboardingApi.uploadKnowledge(userId, file.originFileObj);
          uploaded.push(file.name);
          message.success(`${file.name} 上传成功`);
        }
      }

      setUploadedFiles(uploaded);
      setFileList([]);

      if (uploaded.length > 0) {
        message.success('所有文件上传完成！');
        setTimeout(onComplete, 1500);
      }
    } catch (error) {
      message.error('上传失败，请重试');
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2>步骤 2: 上传知识库文档</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>
        上传产品介绍、FAQ、话术模板等文档，帮助 AI 更好地了解您的业务
      </p>

      <Upload.Dragger
        multiple
        fileList={fileList}
        onChange={({ fileList }) => setFileList(fileList)}
        beforeUpload={() => false}
        accept=".pdf,.txt,.docx,.doc"
      >
        <p className="ant-upload-drag-icon">
          <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">
          支持 PDF、TXT、DOCX 格式，单个文件不超过 10MB
        </p>
      </Upload.Dragger>

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Button
          type="primary"
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
          size="large"
        >
          开始上传
        </Button>
      </div>

      {uploadedFiles.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h4>已上传文件：</h4>
          <List
            dataSource={uploadedFiles}
            renderItem={(item) => (
              <List.Item>
                <FileTextOutlined style={{ marginRight: 8, color: '#52c41a' }} />
                {item}
                <CheckCircleOutlined style={{ marginLeft: 8, color: '#52c41a' }} />
              </List.Item>
            )}
          />
        </div>
      )}

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Button type="link" onClick={onComplete}>
          跳过此步骤
        </Button>
      </div>
    </Card>
  );
}
