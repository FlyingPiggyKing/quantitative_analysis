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
        className="absolute inset-0 backdrop-blur-sm"
        style={{ background: "rgba(8,6,4,0.75)" }}
        onClick={onClose}
      />

      {/* Modal */}
      <div className="vt-panel relative p-6 w-full max-w-sm mx-4 vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-vt-parchment-dim hover:text-vt-brass-300 text-xl transition-colors"
        >
          ×
        </button>

        <div className="text-center mb-6">
          <h2 className="vt-emboss text-3xl mb-2 leading-none">
            {isLogin ? "登 录" : "注 册"}
          </h2>
          <p className="vt-engraved text-sm">{message}</p>
          <hr className="vt-rule mt-3 max-w-[80%] mx-auto" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="vt-input w-full px-4 py-2"
              placeholder="用户名"
              required
            />
          </div>

          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="vt-input w-full px-4 py-2"
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
                className="vt-input w-full px-4 py-2"
                placeholder="确认密码"
                required
              />
            </div>
          )}

          <div>
            <div className="flex gap-3 items-stretch">
              {captcha && (
                <img
                  src={captcha.image}
                  alt="CAPTCHA"
                  className="h-14 sm:h-12 w-auto rounded-sm border border-vt-brass-700 cursor-pointer flex-shrink-0"
                  style={{
                    boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.4), 0 1px 0 rgba(241,214,138,0.08)",
                    imageRendering: "crisp-edges",
                  }}
                  onClick={fetchCaptcha}
                  title="点击刷新"
                />
              )}
              <input
                type="text"
                value={captchaCode}
                onChange={(e) => setCaptchaCode(e.target.value.toUpperCase())}
                className="vt-input flex-1 min-w-0 px-3 py-2"
                placeholder="验证码"
                maxLength={6}
                required
              />
            </div>
          </div>

          {error && (
            <div className="text-vt-oxblood-400 text-sm text-center font-[var(--font-playfair)] italic tracking-wide">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="vt-btn-primary w-full px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "请 稍 候 …" : isLogin ? "登 录" : "注 册"}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={toggleMode}
            className="text-vt-brass-400 hover:text-vt-brass-300 text-sm font-[var(--font-playfair)] italic tracking-wide transition-colors"
          >
            {isLogin ? "没有账号？立即注册" : "已有账号？去登录"}
          </button>
        </div>
      </div>
    </div>
  );
}
