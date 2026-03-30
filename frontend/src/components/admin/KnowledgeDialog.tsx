import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { KnowledgeMetadata } from '@/services/knowledge.service';

interface KnowledgeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveText: (content: string, metadata: KnowledgeMetadata) => Promise<void>;
  onSaveFile: (file: File) => Promise<void>;
  loading?: boolean;
}

export default function KnowledgeDialog({
  open,
  onOpenChange,
  onSaveText,
  onSaveFile,
  loading = false
}: KnowledgeDialogProps) {
  const [activeTab, setActiveTab] = useState('text');
  const [textContent, setTextContent] = useState('');
  const [title, setTitle] = useState('');
  const [source, setSource] = useState('admin-upload');
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (activeTab === 'text') {
      await onSaveText(textContent, { source, title });
    } else {
      if (file) {
        await onSaveFile(file);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>添加知识库内容</DialogTitle>
          <DialogDescription>
            您可以直接输入文本或上传文档文件（PDF, DOCX, TXT）。
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="text">文本输入</TabsTrigger>
            <TabsTrigger value="file">文件上传</TabsTrigger>
          </TabsList>
          
          <form onSubmit={handleSubmit}>
            <TabsContent value="text" className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="title">标题</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="知识点标题"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source">来源</Label>
                <Input
                  id="source"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  placeholder="例如：销售手册 V1"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="content">内容</Label>
                <Textarea
                  id="content"
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="输入详细的知识内容..."
                  className="h-48"
                  required
                />
              </div>
            </TabsContent>

            <TabsContent value="file" className="space-y-4 py-4">
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="file">上传文件</Label>
                <Input 
                  id="file" 
                  type="file" 
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  accept=".pdf,.docx,.txt,.md"
                />
                <p className="text-xs text-muted-foreground">支持 PDF, DOCX, TXT, MD 格式</p>
              </div>
            </TabsContent>

            <DialogFooter className="mt-4">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button 
                type="submit" 
                disabled={loading || (activeTab === 'file' && !file) || (activeTab === 'text' && !textContent)}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {loading ? '上传中...' : '确认添加'}
              </Button>
            </DialogFooter>
          </form>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
