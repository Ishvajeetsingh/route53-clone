"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { API_BASE } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/hosted-zones", label: "Hosted zones" },
  { href: "/traffic-policies", label: "Traffic policies" },
  { href: "/health-checks", label: "Health checks" },
  { href: "/resolver", label: "Resolver" },
  { href: "/profiles", label: "Profiles" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { username, signOut } = useAuth();
  const router = useRouter();

  function handleSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const q = String(data.get("q") ?? "").trim();
    router.push(q ? `/hosted-zones?q=${encodeURIComponent(q)}` : "/hosted-zones");
  }

  return (
    <>
      <header className="console-header">
        <div className="console-brand">
          <span className="aws-mark">
            aws<span>&#63743;</span>
          </span>
          <span className="service-name">Route&nbsp;53</span>
        </div>
        <form className="console-search" onSubmit={handleSearch} role="search">
          <input name="q" placeholder="Search hosted zones" aria-label="Search hosted zones" />
          <button type="submit">Search</button>
        </form>
        <div className="console-meta">
          <span>Global</span>
          <span className="console-user">
            <span>{username ?? "–"}</span>
            <button type="button" onClick={() => void signOut()}>
              Sign out
            </button>
          </span>
        </div>
      </header>
      <nav className="mobile-nav" aria-label="Service navigation">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href}>
            {n.label}
          </Link>
        ))}
      </nav>
      <div className="app-frame">
        <aside className="sidebar" aria-label="Route53 navigation">
          <div className="sidebar-section">Route 53</div>
          {NAV.map((n) => {
            const active = pathname === n.href || (n.href === "/hosted-zones" && pathname.startsWith("/hosted-zones"));
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`nav-item${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <span className="nav-dot" aria-hidden="true" />
                {n.label}
              </Link>
            );
          })}
          <div className="sidebar-section">Resources</div>
          <a className="nav-item" href={`${API_BASE}/api/docs`} target="_blank" rel="noreferrer">
            <span className="nav-dot" aria-hidden="true" />
            API docs
          </a>
        </aside>
        <main className="content">{children}</main>
      </div>
    </>
  );
}
