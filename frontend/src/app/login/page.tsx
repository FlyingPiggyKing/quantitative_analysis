"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/services/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CaptchaData {
  id: number;
  image: string;
}

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [captcha, setCaptcha] = useState<CaptchaData | null>(null);
  const [captchaCode, setCaptchaCode] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login, register, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push("/");
    }
  }, [user, router]);

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

  useEffect(() => {
    fetchCaptcha();
  }, []);

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
        router.push("/");
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

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="vt-emboss text-5xl mb-3 leading-none">Stock Analyzer</h1>
          <p className="vt-engraved">
            {isLogin ? "Sign in to your account" : "Create a new account"}
          </p>
          <hr className="vt-rule mt-4 max-w-sm mx-auto" />
        </div>

        <div className="vt-panel relative p-8 vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-xs font-[var(--font-playfair)] uppercase tracking-[0.2em] text-vt-brass-400 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="vt-input w-full px-4 py-2"
                placeholder="Enter username"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-[var(--font-playfair)] uppercase tracking-[0.2em] text-vt-brass-400 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="vt-input w-full px-4 py-2"
                placeholder="Enter password"
                required
              />
            </div>

            {!isLogin && (
              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-[var(--font-playfair)] uppercase tracking-[0.2em] text-vt-brass-400 mb-2">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="vt-input w-full px-4 py-2"
                  placeholder="Confirm password"
                  required
                />
              </div>
            )}

            <div>
              <label htmlFor="captcha" className="block text-xs font-[var(--font-playfair)] uppercase tracking-[0.2em] text-vt-brass-400 mb-2">
                CAPTCHA Verification
              </label>
              <div className="flex gap-3">
                {captcha && (
                  <img
                    src={captcha.image}
                    alt="CAPTCHA"
                    className="h-12 sm:h-10 rounded-sm border border-vt-brass-700 cursor-pointer flex-shrink-0"
                    style={{ boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.4), 0 1px 0 rgba(241,214,138,0.08)" }}
                    onClick={fetchCaptcha}
                    title="Click to refresh"
                  />
                )}
                <input
                  id="captcha"
                  type="text"
                  value={captchaCode}
                  onChange={(e) => setCaptchaCode(e.target.value.toUpperCase())}
                  className="vt-input flex-1 min-w-0 px-3 py-2"
                  placeholder="验证码"
                  maxLength={6}
                  required
                />
              </div>
              <p className="vt-engraved text-xs mt-2">Click image to refresh</p>
            </div>

            {error && (
              <div className="text-vt-oxblood-400 text-sm text-center font-[var(--font-playfair)] italic tracking-wide">{error}</div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="vt-btn-primary w-full px-4 py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Please wait…" : isLogin ? "Sign In" : "Sign Up"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={toggleMode}
              className="text-vt-brass-400 hover:text-vt-brass-300 text-sm font-[var(--font-playfair)] italic tracking-wide transition-colors"
            >
              {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Sign In"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
