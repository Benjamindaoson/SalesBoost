import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer 
} from 'recharts';
import { Play, BookOpen, Trophy, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { sessionService, Session } from '@/services/session.service';
import { useAuthStore } from '@/store/auth.store';

export default function StudentDashboard() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [stats, setStats] = useState({
    totalTime: 0,
    completedCourses: 0,
    avgScore: 0,
    recentActivity: [] as Session[]
  });

  useEffect(() => {
    const fetchStats = async () => {
      if (!user) return;
      try {
        // Fetch sessions for stats
        const data = await sessionService.listSessions({ user_id: user.id, page_size: 10 });
        setSessions(data.items);
        
        // Simple client-side aggregation (mock logic for now as API is limited)
        const completed = data.items.filter(s => s.status === 'completed');
        const totalScore = completed.reduce((acc, curr) => acc + (curr.final_score || 0), 0);
        
        setStats({
          totalTime: Math.floor(completed.length * 0.5), // Mock: 30 min per session
          completedCourses: completed.length,
          avgScore: completed.length ? Math.round(totalScore / completed.length) : 0,
          recentActivity: data.items.slice(0, 3)
        });
      } catch (error) {
        console.error("Failed to fetch dashboard stats:", error);
      }
    };
    
    fetchStats();
  }, [user]);

  // Mock skill data for radar chart until backend provides it
  const skillData = [
    { subject: 'Opening', A: 120, fullMark: 150 },
    { subject: 'Discovery', A: 98, fullMark: 150 },
    { subject: 'Presentation', A: 86, fullMark: 150 },
    { subject: 'Objection', A: 99, fullMark: 150 },
    { subject: 'Closing', A: 85, fullMark: 150 },
    { subject: 'Follow-up', A: 65, fullMark: 150 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Button onClick={() => navigate('/student/training/course_default')}>
          <Play className="mr-2 h-4 w-4" /> Start Training
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Training Time</CardTitle>
            <Trophy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalTime} Hours</div>
            <p className="text-xs text-muted-foreground">Based on completed sessions</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Sessions</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.completedCourses}</div>
            <p className="text-xs text-muted-foreground">Total sessions finished</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Score</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgScore}%</div>
            <p className="text-xs text-muted-foreground">Across all modules</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Skill Level</CardTitle>
            <Radar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Intermediate</div>
            <p className="text-xs text-muted-foreground">Top 30% of peers</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Skill Analysis</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={skillData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" />
                  <PolarRadiusAxis angle={30} domain={[0, 150]} />
                  <Radar
                    name="My Skills"
                    dataKey="A"
                    stroke="#4f46e5"
                    fill="#4f46e5"
                    fillOpacity={0.6}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-8">
              {stats.recentActivity.length === 0 ? (
                <p className="text-sm text-gray-500">No recent activity.</p>
              ) : (
                stats.recentActivity.map((session) => (
                  <div key={session.id} className="flex items-center">
                    <div className="h-9 w-9 rounded-full bg-indigo-100 flex items-center justify-center">
                      <Play className="h-4 w-4 text-indigo-600" />
                    </div>
                    <div className="ml-4 space-y-1">
                      <p className="text-sm font-medium leading-none">Session: {session.course_id}</p>
                      <p className="text-sm text-muted-foreground">{new Date(session.started_at).toLocaleDateString()}</p>
                    </div>
                    <div className="ml-auto font-medium text-sm">{session.status}</div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
