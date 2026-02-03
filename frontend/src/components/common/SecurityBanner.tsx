import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';

export default function SecurityBanner() {
  const [visible, setVisible] = useState(true);
  const hasExposedKey = !!import.meta.env.VITE_DEEPSEEK_API_KEY;

  if (!visible || !hasExposedKey) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between">
      <div className="flex items-center gap-2 text-amber-800 text-sm">
        <AlertTriangle className="w-4 h-4 text-amber-600" />
        <span>
          <strong>Security Warning:</strong> Running in Demo Mode with Client-Side API Key. 
          This setup is for evaluation only. Do not deploy to production without a backend proxy.
        </span>
      </div>
      <button 
        onClick={() => setVisible(false)}
        className="text-amber-600 hover:text-amber-800"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
