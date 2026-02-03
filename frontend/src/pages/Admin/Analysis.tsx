import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import { ArrowUp, ArrowDown, Minus, Users, GraduationCap, Trophy } from "lucide-react";
import { mockTeamAnalysis, mockAnalysisKPI } from '@/services/adminMockData';

export default function AdminAnalysis() {
  const data = mockTeamAnalysis;
  const kpi = mockAnalysisKPI;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ability Analysis</h1>
          <p className="text-muted-foreground mt-2">Team performance metrics and growth trends.</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Teams</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi.teamsCount}</div>
            <p className="text-xs text-muted-foreground">Across all departments</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Students Trained</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi.oldStudentsCount}</div>
            <p className="text-xs text-muted-foreground">+12% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Score</CardTitle>
            <Trophy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi.averageScore}</div>
            <p className="text-xs text-muted-foreground">Top 10% industry standard</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Weekly Trainings</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi.weeklyTrainingCount}</div>
            <p className="text-xs text-muted-foreground">Sessions completed</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Team Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Team Performance Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="score" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Training Volume Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Training Volume by Team</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="trainingCount" stroke="#8b5cf6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Ranking Table */}
      <Card>
        <CardHeader>
          <CardTitle>Team Rankings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">Rank</TableHead>
                <TableHead>Team Name</TableHead>
                <TableHead>Members</TableHead>
                <TableHead>Avg Score</TableHead>
                <TableHead>Growth Rate</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Trend</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((team) => (
                <TableRow key={team.id}>
                  <TableCell className="font-medium">#{team.rank}</TableCell>
                  <TableCell>{team.name}</TableCell>
                  <TableCell>{team.memberCount}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-bold">{team.score}</span>
                      <Badge variant="outline" className={
                        team.score >= 90 ? "bg-green-50 text-green-700 border-green-200" :
                        team.score >= 80 ? "bg-blue-50 text-blue-700 border-blue-200" :
                        "bg-yellow-50 text-yellow-700 border-yellow-200"
                      }>
                        {team.scoreLabel}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={team.growthRate >= 0 ? "text-green-600" : "text-red-600"}>
                      {team.growthRate > 0 ? "+" : ""}{team.growthRate}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={team.score >= 80 ? "default" : "secondary"}>
                      {team.score >= 80 ? "On Track" : "Needs Attention"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {team.trend === 'up' && <ArrowUp className="h-4 w-4 text-green-500 ml-auto" />}
                    {team.trend === 'down' && <ArrowDown className="h-4 w-4 text-red-500 ml-auto" />}
                    {team.trend === 'stable' && <Minus className="h-4 w-4 text-gray-400 ml-auto" />}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* AI Report Dialog */}
      <Dialog open={isReportOpen} onOpenChange={setIsReportOpen}>
        <DialogContent className="max-w-[800px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-600" />
              AI Performance Analysis
            </DialogTitle>
            <DialogDescription>
              Executive summary generated by DeepSeek V3 based on current performance data.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 prose prose-indigo max-w-none">
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
              {report}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
