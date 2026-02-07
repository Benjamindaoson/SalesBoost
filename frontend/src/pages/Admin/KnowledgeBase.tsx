import { useState, useEffect } from 'react';
import { 
  Search, 
  Plus, 
  MoreVertical, 
  FileText,
  Globe,
  Users
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { knowledgeService, KnowledgeEntry, KnowledgeMetadata } from '@/services/knowledge.service';
import KnowledgeDialog from '@/components/admin/KnowledgeDialog';
import { useToast } from '@/hooks/use-toast';

export default function AdminKnowledgeBase() {
  const [searchTerm, setSearchTerm] = useState("");
  const [items, setItems] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { toast } = useToast();

  const fetchData = async () => {
    try {
      const { items } = await knowledgeService.listKnowledge({ page_size: 20 });
      setItems(items);
    } catch (error) {
      console.error("Failed to load knowledge base", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveText = async (content: string, metadata: KnowledgeMetadata) => {
    setUploading(true);
    try {
      await knowledgeService.uploadText(content, metadata);
      toast({ title: "上传成功", description: "文本内容已添加到知识库" });
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({ title: "上传失败", description: "请稍后重试", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  const handleSaveFile = async (file: File) => {
    setUploading(true);
    try {
      await knowledgeService.uploadFile(file);
      toast({ title: "上传成功", description: "文件已成功上传" });
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({ title: "上传失败", description: "请稍后重试", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">知识管理</h1>
        <p className="text-sm text-gray-500 mt-1">管理知识库和资料</p>
      </div>

      {/* Top Bar */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="relative w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input 
            placeholder="搜索知识库..." 
            className="pl-9 bg-gray-50 border-transparent focus:bg-white transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <Button 
          className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md rounded-lg"
          onClick={() => setDialogOpen(true)}
        >
          <Plus className="w-4 h-4 mr-2" />
          新建知识库
        </Button>
      </div>

      {/* Knowledge Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex-1">
        <Table>
          <TableHeader className="bg-gray-50/50">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[300px] text-gray-500 font-medium">名称</TableHead>
              <TableHead className="text-gray-500 font-medium">来源</TableHead>
              <TableHead className="w-[400px] text-gray-500 font-medium">内容预览</TableHead>
              <TableHead className="text-gray-500 font-medium">类型</TableHead>
              <TableHead className="text-gray-500 font-medium">创建时间</TableHead>
              <TableHead className="text-right text-gray-500 font-medium">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
                <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">加载中...</TableCell>
                </TableRow>
            ) : items.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">暂无知识库条目</TableCell>
                </TableRow>
            ) : (
                items.map((kb) => (
              <TableRow key={kb.id} className="hover:bg-gray-50/50 border-gray-100">
                <TableCell className="py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{kb.title}</div>
                      <div className="text-xs text-gray-400 mt-0.5">ID: {kb.id}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-gray-600 py-4">{kb.metadata.source || '未知'}</TableCell>
                <TableCell className="text-gray-500 text-sm py-4 line-clamp-1">
                    <span className="line-clamp-1 block max-w-[380px]">{kb.content}</span>
                </TableCell>
                <TableCell className="py-4">
                  <Badge variant="outline" className={`font-normal rounded-full px-2.5 py-0.5 gap-1.5 bg-blue-50 text-blue-700 border-blue-200`}>
                    <Globe className="w-3 h-3" />
                    {kb.metadata.type || '文档'}
                  </Badge>
                </TableCell>
                <TableCell className="text-gray-500 text-sm py-4">{new Date(kb.created_at).toLocaleDateString()}</TableCell>
                <TableCell className="text-right py-4">
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            )))}
          </TableBody>
        </Table>
      </div>

      <KnowledgeDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSaveText={handleSaveText}
        onSaveFile={handleSaveFile}
        loading={uploading}
      />
    </div>
  );
}
