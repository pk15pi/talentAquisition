import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/session";
import { Alert } from "../components/ui";
import { login } from "../services/api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  const { refreshSession } = useAuth();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await login(username, password);
      refreshSession();
      navigate("/");
    } catch {
      setError("Login failed. Check your username and password.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_20%_20%,#e2edff,#f5f7fb_55%)] px-4">
      <form className="grid w-full max-w-md gap-4 rounded-2xl border border-line bg-white p-8 shadow-xl" onSubmit={submit}>
        <span className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-teal-400 font-display text-2xl font-extrabold text-white">
          S
        </span>
        <h1 className="font-display text-2xl font-extrabold">Welcome to SynfoTalent</h1>
        <p className="text-sm text-muted">Sign in to your recruitment workspace.</p>
        {error && <Alert>{error}</Alert>}
        <label className="grid gap-1 text-xs font-bold text-slate-600">
          Username
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-normal" value={username} onChange={(event) => setUsername(event.target.value)} required />
        </label>
        <label className="grid gap-1 text-xs font-bold text-slate-600">
          Password
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-normal" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        <button className="rounded-lg bg-brand py-2 font-bold text-white hover:bg-blue-800 disabled:bg-slate-300" disabled={pending}>
          Sign in
        </button>
        <small className="text-xs text-muted">Ask your administrator to create your account.</small>
      </form>
    </div>
  );
}
