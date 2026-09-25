"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/auth";

export default function ComingSoonPage({ title, blurb }: { title: string; blurb: string }) {
  const { username, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !username) router.replace("/login");
  }, [ready, username, router]);

  if (!ready || !username) {
    return (
      <div style={{ padding: 40 }}>
        <span className="spinner" /> Loading console…
      </div>
    );
  }

  return (
    <AppShell>
      <div className="breadcrumbs">
        <Link href="/dashboard">Route 53</Link> &gt; {title}
      </div>
      <h1 className="page-title">{title}</h1>
      <p className="page-subtitle">{blurb}</p>
      <div className="panel coming-soon">
        <div className="panel-header">
          <h2>Not available in this console</h2>
        </div>
        <div className="panel-body">
          <p>
            This feature is not available in this demo console.
          </p>
          <p>
            Continue to <Link href="/hosted-zones">Hosted zones</Link> to manage domains and DNS records.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
