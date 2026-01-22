import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

// Data from Image 2
const standards = [
  {
    id: 1,
    dimension: "完整性",
    desc: "是否覆盖一次有效销售对话中应包含的关键环节（需求挖掘、价值说明、异议回应、推进动作等）",
    scores: [
      { score: 1, text: "完全缺失关键环节，对话零散无结构" },
      { score: 2, text: "仅覆盖部分环节，明显缺漏关键步骤" },
      { score: 3, text: "覆盖主要环节，但顺序或衔接不清晰" },
      { score: 4, text: "基本覆盖完整流程，个别环节略显仓促" },
      { score: 5, text: "完整覆盖销售关键流程，结构清晰、节奏合理" },
    ]
  },
  {
    id: 2,
    dimension: "相关性",
    desc: "回应内容是否紧扣客户真实诉求，而非泛泛而谈或自说自话",
    scores: [
      { score: 1, text: "回答与客户问题基本无关" },
      { score: 2, text: "部分相关，但呈现先后重点略脱离" },
      { score: 3, text: "大体围绕问题，但未精准击中诉求" },
      { score: 4, text: "回答较为贴合客户诉求，重点明确" },
      { score: 5, text: "高度贴合客户真实需求，点对点回应" },
    ]
  },
  {
    id: 3,
    dimension: "正确性",
    desc: "产品、权益、规则等信息是否准确无误",
    scores: [
      { score: 1, text: "完全错误，存在明显误导性表述" },
      { score: 2, text: "大部分内容错误，仅少量正确" },
      { score: 3, text: "核心信息正确，但存在细节中错误或模糊表述" },
      { score: 4, text: "信息基本准确，细节较微小不严谨" },
      { score: 5, text: "信息完全准确，表述清晰，无歧义" },
    ]
  },
  {
    id: 4,
    dimension: "逻辑表达能力",
    desc: "表达是否清晰、有条理，逻辑是否连贯，是否具备说服力",
    scores: [
      { score: 1, text: "表达混乱，逻辑不通，难以理解" },
      { score: 2, text: "逻辑较弱，跳跃明显，说明力不足" },
      { score: 3, text: "基本有逻辑，但层次感与说服力一般" },
      { score: 4, text: "逻辑清晰，表述顺畅，有一定说服力" },
      { score: 5, text: "逻辑严密，表达清楚，说服力强" },
    ]
  },
  {
    id: 5,
    dimension: "合规表现",
    desc: "是否触及、接近或违反合规红线",
    scores: [
      { score: 1, text: "明确违规，存在严重合规风险" },
      { score: 2, text: "接近红线，存在明显合规隐患" },
      { score: 3, text: "无明显违规，但表达不够审慎" },
      { score: 4, text: "基本合规，个别表述可进一步规范" },
      { score: 5, text: "完全合规，表达规范，边界清晰" },
    ]
  }
];

export function StandardsTab() {
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader className="bg-slate-50">
          <TableRow>
            <TableHead className="w-[120px] font-bold text-slate-900">评估维度</TableHead>
            <TableHead className="w-[200px] font-bold text-slate-900">评估维度描述</TableHead>
            <TableHead className="font-bold text-slate-900">打分标准</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {standards.map((item) => (
            <TableRow key={item.id} className="hover:bg-slate-50/50">
              <TableCell className="font-medium align-top py-4">{item.dimension}</TableCell>
              <TableCell className="text-slate-600 align-top py-4 text-sm leading-relaxed">
                {item.desc}
              </TableCell>
              <TableCell className="py-4">
                <div className="space-y-2">
                  {item.scores.map((s) => (
                    <div key={s.score} className="flex gap-2 text-sm">
                      <span className="font-bold text-slate-900 min-w-[30px]">{s.score}分：</span>
                      <span className="text-slate-600">{s.text}</span>
                    </div>
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
