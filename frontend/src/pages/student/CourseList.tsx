import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function CourseList() {
  const courses = [
    { id: 1, title: 'B2B Sales Fundamentals', progress: 100, status: 'Completed' },
    { id: 2, title: 'Advanced Negotiation', progress: 45, status: 'In Progress' },
    { id: 3, title: 'Closing Techniques', progress: 0, status: 'Not Started' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => (
          <Card key={course.id}>
            <CardHeader>
              <CardTitle>{course.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm text-muted-foreground">{course.status}</span>
                <span className="text-sm font-medium">{course.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
                <div 
                  className="bg-indigo-600 h-2.5 rounded-full" 
                  style={{ width: `${course.progress}%` }}
                ></div>
              </div>
              <Button className="w-full">
                {course.status === 'Completed' ? 'Review' : 'Continue'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
