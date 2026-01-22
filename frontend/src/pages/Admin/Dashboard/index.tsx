import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, Trophy, Target, TrendingUp } from "lucide-react";

const stats = [
  { label: "参与团队", value: "6", unit: "个销售团队", icon: Users, color: "text-purple-600", bg: "bg-purple-50" },
  { label: "总参与人数", value: "103", unit: "名学员", icon: Users, color: "text-blue-600", bg: "bg-blue-50" },
  { label: "平均得分", value: "84.1", unit: "整体水平良好", icon: Trophy, color: "text-green-600", bg: "bg-green-50" },
  { label: "总训练次数", value: "1539", unit: "累计训练", icon: Target, color: "text-yellow-600", bg: "bg-yellow-50" },
];

const teamRankings = [
  {
    rank: 1,
    name: "直销一队",
    manager: "张经理",
    members: 15,
    trainings: 245,
    growth: "+ 8.5%",
    score: 92.5,
    strengths: ["需求探寻", "产品介绍"],
    weaknesses: ["异议处理"],
  },
  {
    rank: 2,
    name: "直销二队",
    manager: "李经理",
    members: 18,
    trainings: 312,
    growth: "+ 6.2%",
    score: 88.3,
    strengths: ["开场破冰", "权益介绍"],
    weaknesses: ["跟进成交"],
  },
  {
    rank: 3,
    name: "渠道拓展部",
    manager: "王总监",
    members: 12,
    trainings: 189,
    growth: "+ 4.1%",
    score: 85.6,
    strengths: ["商务礼仪", "谈判技巧"],
    weaknesses: ["产品知识"],
  },
];

export default function AdminDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">能力分析</h1>
        <p className="text-slate-500">查看学员能力分析数据</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-slate-200 shadow-sm hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-sm font-medium text-slate-500 mb-2">{stat.label}</p>
                  <div className="text-3xl font-bold text-slate-900 mb-1">{stat.value}</div>
                  <p className="text-xs text-slate-400">{stat.unit}</p>
                </div>
                <div className={`p-3 rounded-xl ${stat.bg}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Rankings */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-slate-900">团队能力排行</h2>
          <p className="text-sm text-slate-500">按平均分倒序排名</p>
        </div>

        <div className="space-y-4">
          {teamRankings.map((team) => (
            <div key={team.rank} className="flex flex-col md:flex-row items-center gap-6 p-4 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-white hover:shadow-md transition-all">
              {/* Rank Badge */}
              <div className={`
                flex items-center justify-center w-12 h-12 rounded-lg text-white font-bold text-xl shadow-sm flex-shrink-0
                ${team.rank === 1 ? "bg-yellow-400" : team.rank === 2 ? "bg-slate-400" : team.rank === 3 ? "bg-amber-600" : "bg-slate-200 text-slate-500"}
              `}>
                {team.rank}
              </div>

              {/* Team Info */}
              <div className="flex-1 min-w-[200px]">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-bold text-slate-900">{team.name}</h3>
                  <Badge variant="outline" className="text-xs font-normal text-slate-500 border-slate-200">
                    负责人：{team.manager}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>{team.members} 人</span>
                  <span>{team.trainings} 次训练</span>
                  <span className="text-green-600 font-medium flex items-center gap-0.5">
                    <TrendingUp className="h-3 w-3" /> {team.growth}
                  </span>
                </div>
              </div>

              {/* Score */}
              <div className="flex flex-col items-center justify-center min-w-[100px] px-4 border-l border-r border-slate-200/50">
                <div className="text-3xl font-bold text-blue-600">{team.score}</div>
                <div className="text-xs text-slate-400">平均分</div>
              </div>

              {/* Tags */}
              <div className="flex-1 space-y-2 min-w-[200px]">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-12">优势：</span>
                  <div className="flex flex-wrap gap-1">
                    {team.strengths.map(tag => (
                      <Badge key={tag} variant="secondary" className="bg-green-50 text-green-700 hover:bg-green-100 border-green-100 text-[10px] px-1.5 py-0.5">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-12">待提升：</span>
                  <div className="flex flex-wrap gap-1">
                    {team.weaknesses.map(tag => (
                      <Badge key={tag} variant="secondary" className="bg-orange-50 text-orange-700 hover:bg-orange-100 border-orange-100 text-[10px] px-1.5 py-0.5">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
