import {
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  ChartNoAxesCombined,
  FileText,
  LayoutDashboard,
  LogOut,
  Receipt,
  Settings,
  ShieldAlert,
  UserRound,
  Users,
  WalletCards,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { NAV } from "../auth/navigation";
import { useAuth } from "../auth/session";
import { ROLE_LABELS, displayName } from "../auth/types";

const ICONS: Record<string, LucideIcon> = {
  "/": LayoutDashboard,
  "/clients": Building2,
  "/jobs": BriefcaseBusiness,
  "/candidates": Users,
  "/duplicates": ShieldAlert,
  "/applications": FileText,
  "/interviews": CalendarClock,
  "/submissions": WalletCards,
  "/placements": UserRound,
  "/billing": Receipt,
  "/reports": ChartNoAxesCombined,
  "/users": Users,
  "/settings": Settings,
};

export default function Layout() {
  const { user, can, signOut } = useAuth();
  const navigate = useNavigate();
  const links = NAV.filter((item) => item.allow(can));
  const name = user ? displayName(user) : "";
  const role = user ? ROLE_LABELS[user.role] || user.role : "";

  return (
    <div className="min-h-screen bg-canvas md:grid md:grid-cols-[250px_1fr]">
      <aside className="bg-navy text-slate-200 md:sticky md:top-0 md:flex md:h-screen md:flex-col md:px-4 md:py-6">
        <div className="flex items-center gap-3 px-3 py-4 md:pb-8">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-teal-400 font-display text-lg font-extrabold text-white">
            S
          </span>
          <div>
            <b className="block font-display text-white">SynfoTalent</b>
            <small className="text-[11px] text-slate-400">Synfowebs</small>
          </div>
        </div>
        <nav className="flex gap-2 overflow-x-auto px-3 pb-3 md:grid md:gap-1 md:overflow-visible md:px-0">
          {links.map((item) => {
            const Icon = ICONS[item.to] || LayoutDashboard;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm ${isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"}`
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <button
          type="button"
          className="mx-3 mb-3 mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-800 hover:text-white md:mx-0 md:mb-0 md:mt-auto"
          onClick={() => {
            signOut();
            navigate("/login");
          }}
        >
          <LogOut size={17} /> Sign out
        </button>
      </aside>
      <div className="min-w-0">
        <header className="flex items-center justify-between border-b border-line bg-white px-5 py-4">
          <div>
            <p className="text-[11px] font-bold tracking-[0.14em] text-muted">SYNFOWEBS · TALENT SOLUTIONS</p>
            <h2 className="font-display text-base font-bold">Recruitment workspace</h2>
          </div>
          <div className="text-right text-sm">
            <div className="font-semibold">{name}</div>
            <div className="text-xs text-muted">{role}</div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
