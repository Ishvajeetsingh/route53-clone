"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Summary {
  hosted_zones: number;
  records: number;
}

export default function DashboardPage() {
  const { username, ready } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && !username) router.replace("/login");
  }, [ready, username, router]);

  useEffect(() => {
    if (!ready || !username) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api<Summary>("/api/stats/summary");
        if (!cancelled) setSummary(res);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load account summary.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [ready, username]);

  if (!ready || !username) {
    return (
      <div style={{ padding: 40 }}>
        <span className="spinner" /> Loading console…
      </div>
    );
  }

  return (
    <AppShell>
      <div className="breadcrumbs">Route 53 &gt; Dashboard</div>
      <h1 className="page-title">Route 53 Dashboard</h1>
      <p className="page-subtitle">
        Scalable DNS and domain management. Hosted zones hold the DNS records that route traffic for your domains.
      </p>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div className="stat-row">
        <div className="stat-card">
          <div className="k">Hosted zones</div>
          <div className="v">{loading ? "…" : summary?.hosted_zones ?? "–"}</div>
          <div className="k">
            <Link href="/hosted-zones">View hosted zones</Link>
          </div>
        </div>
        <div className="stat-card">
          <div className="k">DNS records</div>
          <div className="v">{loading ? "…" : summary?.records ?? "–"}</div>
          <div className="k">Across all hosted zones</div>
        </div>
        <div className="stat-card">
          <div className="k">Region</div>
          <div className="v" style={{ fontSize: 17 }}>Global</div>
          <div className="k">Route 53 is a global service</div>
        </div>
        <div className="stat-card">
          <div className="k">Signed in as</div>
          <div className="v" style={{ fontSize: 17 }}>{username}</div>
          <div className="k">Local console session</div>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-header">
          <h2>Common tasks</h2>
        </div>
        <div className="panel-body">
          <p style={{ marginTop: 0 }}>
            <Link href="/hosted-zones">Browse hosted zones</Link> to list, search, and open a zone. Inside a zone you
            can create and manage DNS records (A, AAAA, CNAME, TXT, MX, NS, PTR, SRV, CAA, SOA).
          </p>
          <div className="toolbar">
            <button className="btn btn-primary" onClick={() => router.push("/hosted-zones")}>
              View hosted zones
            </button>
            <button className="btn" onClick={() => router.push("/hosted-zones?create=1")}>
              Create hosted zone
            </button>
          </div>
          <p style={{ color: "#5f6b6a", fontSize: 12.5, marginBottom: 0 }}>
            New hosted zones start with system-managed NS and SOA records at the zone apex. Those records can be
            edited but cannot be deleted.
          </p>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>About this console</h2>
        </div>
        <div className="panel-body">
          <p style={{ marginTop: 0 }}>
            This is a Route 53 management-console clone for DNS administration. It manages hosted zones and record
            sets only — it does not perform live DNS resolution.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
