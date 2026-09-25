"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import ConfirmModal from "@/components/ConfirmModal";
import Pagination from "@/components/Pagination";
import ZoneModal from "@/components/ZoneModal";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { HostedZone, Paginated } from "@/types";

const PAGE_SIZE = 20;

export default function HostedZonesPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40 }}><span className="spinner" /> Loading console…</div>}>
      <HostedZonesInner />
    </Suspense>
  );
}

function HostedZonesInner() {
  const { username, ready } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const notify = useToast();

  const [q, setQ] = useState(params.get("q") ?? "");
  const [debouncedQ, setDebouncedQ] = useState(params.get("q") ?? "");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<HostedZone> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<HostedZone | null>(null);
  const [deleting, setDeleting] = useState<HostedZone | null>(null);
  const [busy, setBusy] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const urlQ = params.get("q") ?? "";
  const createRequested = params.get("create") === "1";

  useEffect(() => {
    if (ready && !username) router.replace("/login");
  }, [ready, username, router]);

  useEffect(() => {
    // Keep the toolbar in sync with header search / back-forward navigation.
    setQ(urlQ);
    setDebouncedQ(urlQ);
    setPage(1);
  }, [urlQ]);

  useEffect(() => {
    if (createRequested) {
      setModalError(null);
      setShowCreate(true);
    }
  }, [createRequested]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(t);
  }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api<Paginated<HostedZone>>(
        `/api/hosted-zones?q=${encodeURIComponent(debouncedQ)}&page=${page}&page_size=${PAGE_SIZE}`
      );
      if (res.items.length === 0 && res.page > 1) {
        // Deletions can strand the user on a now-empty page; step back instead.
        setPage(res.page - 1);
        return;
      }
      setData(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load hosted zones.");
    } finally {
      setLoading(false);
    }
  }, [debouncedQ, page]);

  useEffect(() => {
    if (ready && username) void load();
  }, [ready, username, load]);

  async function handleCreate(values: { name?: string; description: string; type: "Public" | "Private" }) {
    setBusy(true);
    setModalError(null);
    try {
      await api("/api/hosted-zones", { method: "POST", body: JSON.stringify(values) });
      setShowCreate(false);
      notify({ kind: "success", title: "Hosted zone created", message: values.name });
      await load();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Create failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEdit(values: { description: string; type: "Public" | "Private" }) {
    if (!editing) return;
    setBusy(true);
    setModalError(null);
    try {
      await api(`/api/hosted-zones/${editing.id}`, { method: "PATCH", body: JSON.stringify(values) });
      setEditing(null);
      notify({ kind: "success", title: "Hosted zone updated", message: editing.name });
      await load();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await api(`/api/hosted-zones/${deleting.id}`, { method: "DELETE" });
      setDeleting(null);
      notify({ kind: "success", title: "Hosted zone deleted", message: `${deleting.name} and its records were removed.` });
      await load();
    } catch (err) {
      notify({ kind: "error", title: "Delete failed", message: err instanceof ApiError ? err.message : "Unknown error" });
    } finally {
      setBusy(false);
    }
  }

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
        <Link href="/dashboard">Route 53</Link> &gt; Hosted zones
      </div>
      <h1 className="page-title">Hosted zones</h1>
      <p className="page-subtitle">
        A hosted zone is a container for records that define how traffic is routed for a domain. Deleting a zone
        deletes all records it contains.
      </p>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div className="panel">
        <div className="panel-header">
          <h2>Hosted zones ({data?.total ?? 0})</h2>
          <div className="toolbar">
            <input type="search" placeholder="Search by domain name" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search hosted zones" />
            <button className="btn" onClick={() => void load()} disabled={loading}>
              Refresh
            </button>
            <button className="btn btn-primary" onClick={() => { setModalError(null); setShowCreate(true); }}>
              Create hosted zone
            </button>
          </div>
        </div>
        <div className="panel-body flush">
          {loading ? (
            <div style={{ padding: 28 }}>
              <span className="spinner" /> Loading hosted zones…
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="empty-state">
              <h3>{debouncedQ ? "No hosted zones match your search" : "No hosted zones yet"}</h3>
              <p>
                {debouncedQ ? (
                  <>
                    Try a different search, or <button className="btn-link" onClick={() => setQ("")}>clear the search</button>.
                  </>
                ) : (
                  "Create your first hosted zone to start managing DNS records."
                )}
              </p>
              {!debouncedQ ? (
                <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                  Create hosted zone
                </button>
              ) : null}
            </div>
          ) : (
            <div className="table-wrap">
              <table className="aws-table">
                <thead>
                  <tr>
                    <th>Domain name</th>
                    <th>Zone ID</th>
                    <th>Type</th>
                    <th>Records</th>
                    <th>Comment</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((z) => (
                    <tr key={z.id}>
                      <td>
                        <Link href={`/hosted-zones/${z.id}`}>{z.name}</Link>
                      </td>
                      <td style={{ fontFamily: "Consolas, Menlo, monospace", fontSize: 12 }}>{z.id}</td>
                      <td>
                        <span className={`pill ${z.type === "Public" ? "public" : ""}`}>{z.type}</span>
                      </td>
                      <td>{z.record_count}</td>
                      <td style={{ maxWidth: 260 }}>{z.description || <span style={{ color: "#879596" }}>—</span>}</td>
                      <td style={{ whiteSpace: "nowrap" }}>{formatDate(z.created_at)}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        <Link href={`/hosted-zones/${z.id}`}>View</Link>
                        {" · "}
                        <button className="btn-link" onClick={() => { setEditing(z); setModalError(null); }}>
                          Edit
                        </button>
                        {" · "}
                        <button className="btn-link" onClick={() => setDeleting(z)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {data && data.total > 0 ? (
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        ) : null}
      </div>

      {showCreate ? (
        <ZoneModal
          title="Create hosted zone"
          initial={{ name: "", description: "", type: "Public" }}
          busy={busy}
          error={modalError}
          onClose={() => setShowCreate(false)}
          onSubmit={handleCreate}
        />
      ) : null}

      {editing ? (
        <ZoneModal
          title={`Edit hosted zone — ${editing.name}`}
          initial={{ name: editing.name, description: editing.description, type: editing.type }}
          busy={busy}
          error={modalError}
          onClose={() => setEditing(null)}
          onSubmit={handleEdit}
        />
      ) : null}

      {deleting ? (
        <ConfirmModal
          title={`Delete hosted zone ${deleting.name}?`}
          body={
            <div>
              <p>
                This permanently deletes hosted zone <strong>{deleting.name}</strong>, including all{" "}
                {deleting.record_count} record(s) in the zone. This action cannot be undone.
              </p>
            </div>
          }
          confirmLabel="Delete hosted zone"
          busy={busy}
          onCancel={() => setDeleting(null)}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
    </AppShell>
  );
}
