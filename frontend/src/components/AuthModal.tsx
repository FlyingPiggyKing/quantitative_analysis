"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/services/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CaptchaData {
  id: number;
  image: string;
}

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
}

export default function AuthModal({ isOpen, onClose, message = "登录后即可使用该功能" }: AuthModalProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [captcha, setCaptcha] = useState<CaptchaData | null>(null);
  const [captchaCode, setCaptchaCode] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login, register } = useAuth();

  useEffect(() => {
    if (isOpen) {
      fetchCaptcha();
    }
  }, [isOpen]);

  const fetchCaptcha = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/captcha`);
      if (res.ok) {
        const data = await res.json();
        setCaptcha(data);
        setCaptchaCode("");
      }
    } catch (e) {
      console.error("Failed to fetch captcha", e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!captcha) {
      setError("Please wait for CAPTCHA to load");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsLoading(true);
    try {
      if (isLogin) {
        await login(username, password, captcha.id, captchaCode);
        onClose();
        window.location.reload();
      } else {
        await register(username, password, captcha.id, captchaCode);
        setError("");
        alert("Registration successful! Please login.");
        setIsLogin(true);
        fetchCaptcha();
      }
    } catch (e: any) {
      setError(e.message || "An error occurred");
      fetchCaptcha();
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError("");
    setPassword("");
    setConfirmPassword("");
    fetchCaptcha();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-slate-800 rounded-lg p-6 w-full max-w-sm mx-4 shadow-2xl border border-slate-700">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-slate-400 hover:text-white text-xl"
        >
          ×
        </button>

        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-white mb-1">
            {isLogin ? "登录" : "注册"}
          </h2>
          <p className="text-slate-400 text-sm">{message}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="用户名"
              required
            />
          </div>

          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="密码"
              required
            />
          </div>

          {!isLogin && (
            <div>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="确认密码"
                required
              />
            </div>
          )}

          <div>
            <div className="flex gap-3">
              {captcha && (
                <img
                  src={captcha.image}
                  alt="CAPTCHA"
                  className="h-10 rounded border border-slate-600 cursor-pointer"
                  onClick={fetchCaptcha}
                  title="点击刷新"
                />
              )}
              <input
                type="text"
                value={captchaCode}
                onChange={(e) => setCaptchaCode(e.target.value.toUpperCase())}
                className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="验证码"
                maxLength={6}
                required
              />
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm text-center">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-medium rounded-lg transition-colors"
          >
            {isLoading ? "请稍候..." : isLogin ? "登录" : "注册"}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={toggleMode}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {isLogin ? "没有账号？立即注册" : "已有账号？去登录"}
          </button>
        </div>
      </div>
    </div>
  );
}
