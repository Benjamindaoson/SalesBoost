import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

const radarData = [
  { subject: 'Opening', A: 120, fullMark: 150 },
  { subject: 'Discovery', A: 98, fullMark: 150 },
  { subject: 'Presentation', A: 86, fullMark: 150 },
  { subject: 'Objection', A: 99, fullMark: 150 },
  { subject: 'Closing', A: 85, fullMark: 150 },
  { subject: 'Follow-up', A: 65, fullMark: 150 },
];

const historyData = [
  { name: 'Session 1', score: 65 },
  { name: 'Session 2', score: 72 },
  { name: 'Session 3', score: 78 },
  { name: 'Session 4', score: 85 },
];

export default function Evaluation() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Evaluation & Feedback</h1>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Skill Radar</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
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
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Performance Trend</CardTitle>
          </CardHeader>
          <CardContent>
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
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-100 rounded-lg">
              <h3 className="font-semibold text-green-900">Strength: Objection Handling</h3>
              <p className="text-green-800 text-sm mt-1">
                You effectively acknowledged the customer's concern about pricing and pivoted to value proposition.
              </p>
            </div>
            <div className="p-4 bg-amber-50 border border-amber-100 rounded-lg">
              <h3 className="font-semibold text-amber-900">Improvement Area: Closing</h3>
              <p className="text-amber-800 text-sm mt-1">
                Try to use a more direct closing technique next time. You hesitated when the customer showed buying signals.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
