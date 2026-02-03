import { useQuery } from '@tanstack/react-query';
import { sessionService } from '@/services/session.service';
import { useAuthStore } from '@/store/auth.store';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AlertCircle } from 'lucide-react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { useMemo } from 'react';

export default function Evaluation() {
  const { user } = useAuthStore();

  // Fetch user's completed sessions
  const { data: sessionsData, isLoading: sessionsLoading } = useQuery({
    queryKey: ['user-sessions', user?.id],
    queryFn: () => sessionService.listSessions({
      user_id: user?.id,
      status: 'completed',
    }),
    enabled: !!user?.id,
  });

  // Fetch latest session review for skill breakdown
  const latestSessionId = sessionsData?.items?.[0]?.id;
  const { data: reviewData, isLoading: reviewLoading, isError, error, refetch } = useQuery({
    queryKey: ['session-review', latestSessionId],
    queryFn: () => sessionService.getSessionReview(latestSessionId || ''),
    enabled: !!latestSessionId,
  });

  const isLoading = sessionsLoading || reviewLoading;

  // Transform skill data for radar chart
  const radarData = useMemo(() => {
    if (!reviewData?.skill_improvement) {
      return [];
    }

    const skills = reviewData.skill_improvement;
    return [
      { subject: 'Opening', score: skills.opening || 0, fullMark: 100 },
      { subject: 'Discovery', score: skills.discovery || 0, fullMark: 100 },
      { subject: 'Presentation', score: skills.presentation || 0, fullMark: 100 },
      { subject: 'Objection', score: skills.objection || 0, fullMark: 100 },
      { subject: 'Closing', score: skills.closing || 0, fullMark: 100 },
      { subject: 'Follow-up', score: skills.followup || 0, fullMark: 100 },
    ];
  }, [reviewData]);

  // Transform session history for bar chart
  const historyData = useMemo(() => {
    if (!sessionsData?.items) return [];

    return sessionsData.items
      .slice(0, 5)
      .reverse()
      .map((session, index) => ({
        name: `Session ${index + 1}`,
        score: Math.round(Math.random() * 30 + 70), // TODO: Get actual score from session
        date: new Date(session.created_at).toLocaleDateString(),
      }));
  }, [sessionsData]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Evaluation & Feedback</h1>
        <DashboardSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Evaluation & Feedback</h1>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-800 mb-4">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">Failed to load evaluation data</p>
            </div>
            <p className="text-sm text-red-700 mb-4">
              {error instanceof Error ? error.message : 'An error occurred while loading your evaluation'}
            </p>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!sessionsData?.items || sessionsData.items.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Evaluation & Feedback</h1>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">No evaluation data available yet</p>
              <p className="text-sm text-muted-foreground mb-6">
                Complete your first training session to see your evaluation and feedback
              </p>
              <Button asChild>
                <a href="/student/training">Start Training</a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Evaluation & Feedback</h1>
        <p className="text-sm text-muted-foreground">
          Based on {sessionsData.items.length} completed {sessionsData.items.length === 1 ? 'session' : 'sessions'}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Skill Radar</CardTitle>
          </CardHeader>
          <CardContent>
            {radarData.length > 0 ? (
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} />
                    <Radar
                      name="My Skills"
                      dataKey="score"
                      stroke="#4f46e5"
                      fill="#4f46e5"
                      fillOpacity={0.6}
                    />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No skill data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Performance Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {historyData.length > 0 ? (
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={historyData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="score" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                Complete more sessions to see your trend
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          {reviewData?.effective_adoptions && reviewData.effective_adoptions.length > 0 ? (
            <div className="space-y-4">
              {reviewData.effective_adoptions.slice(0, 3).map((feedback, index) => (
                <div key={index} className="p-4 bg-green-50 border border-green-100 rounded-lg">
                  <h3 className="font-semibold text-green-900">Strength: {feedback.strategy || 'Good Performance'}</h3>
                  <p className="text-green-800 text-sm mt-1">
                    {feedback.description || 'You demonstrated effective techniques in this area.'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No feedback available yet. Complete more training sessions to receive personalized feedback.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
