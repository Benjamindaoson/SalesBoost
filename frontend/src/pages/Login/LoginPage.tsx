import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "@/services/api";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setError("");
    setLoading(true);

    try {
      await authService.login(username);
      navigate("/");
    } catch (err) {
      console.error(err);
      setError("登录失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        <div className="text-center mb-8">
          <img src="/favicon.svg" alt="Logo" className="w-12 h-12 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900">SalesBoost 登录</h1>
          <p className="text-sm text-gray-500 mt-2">请输入任意用户名进入系统</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={cn(
                "w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50",
                error ? "border-red-500" : "border-gray-300"
              )}
              placeholder="例如: admin"
              autoFocus
            />
          </div>

          {error && <div className="text-sm text-red-500">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-white py-2 px-4 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "登录中..." : "进入系统"}
          </button>
        </form>
      </div>
    </div>
  );
}
