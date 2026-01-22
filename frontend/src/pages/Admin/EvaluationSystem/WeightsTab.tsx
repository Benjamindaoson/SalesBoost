import { useState, useEffect } from "react";
import { Slider } from "@/components/ui/slider";
import { Info } from "lucide-react";

interface WeightConfig {
  id: number;
  name: string;
  weight: number;
}

// Initial data from the user requirement (Image 4)
const initialWeights: WeightConfig[] = [
  { id: 1, name: "完整性", weight: 20 },
  { id: 2, name: "相关性", weight: 20 },
  { id: 3, name: "正确性", weight: 25 },
  { id: 4, name: "逻辑表达能力", weight: 20 },
  { id: 5, name: "合规表现", weight: 15 },
];

export function WeightsTab() {
  const [weights, setWeights] = useState<WeightConfig[]>(initialWeights);
  const [totalWeight, setTotalWeight] = useState(100);

  useEffect(() => {
    const total = weights.reduce((sum, item) => sum + item.weight, 0);
    setTotalWeight(total);
  }, [weights]);

  const handleWeightChange = (id: number, newValue: number[]) => {
    setWeights(weights.map(w => w.id === id ? { ...w, weight: newValue[0] } : w));
  };

  return (
    <div className="space-y-8">
      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 text-blue-900">
        <h3 className="font-bold mb-2">权重配置说明</h3>
        <p className="text-sm opacity-90">
          配置不同维度在总分中的权重占比，所有维度权重之和应为 100%。权重越高，该维度对最终得分的影响越大。
        </p>
      </div>

      {/* Sliders */}
      <div className="space-y-8 px-4">
        {weights.map((item) => (
          <div key={item.id} className="flex items-center gap-6">
            <div className="w-32 flex items-center gap-2 font-medium text-slate-700">
              <span className="p-1.5 bg-slate-100 rounded-md">
                <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </span>
              {item.name}
            </div>
            
            <div className="flex-1">
              <Slider
                value={[item.weight]}
                max={100}
                step={1}
                onValueChange={(val) => handleWeightChange(item.id, val)}
                className="py-4"
              />
            </div>

            <div className="w-16 text-right font-bold text-blue-600 text-lg">
              {item.weight}%
            </div>
          </div>
        ))}
      </div>

      {/* Footer Total */}
      <div className="flex justify-end items-center pt-8 border-t border-slate-100">
        <div className="text-lg font-bold text-slate-900 mr-4">总权重</div>
        <div className={`text-2xl font-bold ${totalWeight === 100 ? 'text-green-600' : 'text-red-500'}`}>
          {totalWeight}%
        </div>
      </div>
    </div>
  );
}
