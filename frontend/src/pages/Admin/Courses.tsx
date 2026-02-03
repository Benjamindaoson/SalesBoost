import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Edit, Trash, Eye, Search, Sparkles, Loader2, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { mockAdminCourses } from '@/services/adminMockData';
import { llmService, ChatMessage } from '@/services/llm.service';
import { useToast } from "@/hooks/use-toast";
import { AdminCourse } from '@/types/admin';

export default function AdminCourses() {
  const [searchTerm, setSearchTerm] = useState('');
  const [courses, setCourses] = useState(mockAdminCourses);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiTopic, setAiTopic] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

  const filteredCourses = courses.filter(course => 
    course.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    course.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleGenerateCourse = async () => {
    if (!aiTopic.trim()) return;
    
    setIsGenerating(true);
    try {
      const systemPrompt = llmService.createCourseOutlinePrompt();
      const messages: ChatMessage[] = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Generate a sales training course outline for: ${aiTopic}` }
      ];

      const response = await llmService.chatCompletion(messages, true);
      
      // Clean JSON string
      const jsonString = response.replace(/```json\n|\n```/g, '');
      const courseData = JSON.parse(jsonString);

      const newCourse: AdminCourse = {
        id: Date.now().toString(),
        title: courseData.title,
        description: courseData.description,
        author: 'AI Generator',
        studentCount: 0,
        popularity: 0,
        rating: 0,
        category: 'AI Generated',
        tags: courseData.tags || ['AI'],
        status: 'draft'
      };

      setCourses([newCourse, ...courses]);
      setIsAiModalOpen(false);
      setAiTopic('');
      
      toast({
        title: "Course Generated!",
        description: `Successfully created draft for "${newCourse.title}"`,
      });

    } catch (error) {
      console.error("Course Generation Error:", error);
      toast({
        variant: "destructive",
        title: "Generation Failed",
        description: "Could not generate course content. Please try again."
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Course Management</h1>
          <p className="text-muted-foreground mt-2">Create and manage training courses.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsAiModalOpen(true)} className="border-indigo-200 text-indigo-700 hover:bg-indigo-50">
            <Sparkles className="mr-2 h-4 w-4" /> AI Create
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" /> Create Course
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>All Courses ({filteredCourses.length})</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search courses..." 
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredCourses.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">No courses found</p>
              <Button variant="outline" onClick={() => setSearchTerm('')}>
                Clear Search
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Stats</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCourses.map((course) => (
                  <TableRow key={course.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{course.title}</div>
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {course.description}
                        </div>
                        <div className="flex gap-1 mt-1">
                          {course.tags?.map(tag => (
                            <Badge key={tag} variant="secondary" className="text-xs px-1 py-0">{tag}</Badge>
                          ))}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{course.category}</TableCell>
                    <TableCell>{course.author}</TableCell>
                    <TableCell>
                      <div className="text-xs space-y-1">
                        <div>Students: {course.studentCount}</div>
                        <div>Rating: {course.rating}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={course.status === 'published' ? 'default' : 'secondary'}>
                        {course.status === 'published' ? 'Published' : 'Draft'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end space-x-2">
                        <Button variant="ghost" size="icon" title="View details">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Edit course">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          title="Delete course"
                        >
                          <Trash className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* AI Generator Modal */}
      <Dialog open={isAiModalOpen} onOpenChange={setIsAiModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-600" />
              AI Course Generator
            </DialogTitle>
            <DialogDescription>
              Enter a sales topic, and our AI will generate a complete course outline for you.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="topic">Course Topic</Label>
              <Input
                id="topic"
                placeholder="e.g., Handling Price Objections for Enterprise Software"
                value={aiTopic}
                onChange={(e) => setAiTopic(e.target.value)}
                disabled={isGenerating}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAiModalOpen(false)} disabled={isGenerating}>
              Cancel
            </Button>
            <Button onClick={handleGenerateCourse} disabled={!aiTopic.trim() || isGenerating} className="bg-indigo-600 hover:bg-indigo-700">
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Course
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
