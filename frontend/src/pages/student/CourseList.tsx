import { useQuery } from '@tanstack/react-query';
import { courseService } from '@/services/course.service';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/skeleton";
import { AlertCircle } from 'lucide-react';

export default function CourseList() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['user-courses'],
    queryFn: () => courseService.listUserCourses(),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-800 mb-4">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">Failed to load courses</p>
            </div>
            <p className="text-sm text-red-700 mb-4">
              {error instanceof Error ? error.message : 'An error occurred while loading courses'}
            </p>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const courses = data?.items || [];

  if (courses.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">No courses available yet</p>
              <p className="text-sm text-muted-foreground">
                Check back later for new courses or contact your administrator
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
        <p className="text-sm text-muted-foreground">
          {courses.length} {courses.length === 1 ? 'course' : 'courses'}
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => (
          <Card key={course.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle>{course.title}</CardTitle>
              {course.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {course.description}
                </p>
              )}
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                <span className={`text-sm font-medium px-2 py-1 rounded ${
                  course.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : course.status === 'in_progress'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {course.status === 'completed' ? 'Completed' :
                   course.status === 'in_progress' ? 'In Progress' : 'Not Started'}
                </span>
                <span className="text-sm font-medium">{course.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
                <div
                  className="bg-indigo-600 h-2.5 rounded-full transition-all"
                  style={{ width: `${course.progress}%` }}
                ></div>
              </div>
              <Button className="w-full" asChild>
                <a href={`/student/training/${course.id}`}>
                  {course.status === 'completed' ? 'Review' : 'Continue'}
                </a>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
