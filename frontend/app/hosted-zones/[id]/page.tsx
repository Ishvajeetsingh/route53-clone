"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import ConfirmModal from "@/components/ConfirmModal";
import Pagination from "@/components/Pagination";
import RecordModal, { type RecordFormValues } from "@/components/RecordModal";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatTtl, isSystemRecord } from "@/lib/format";
import { RECORD_TYPES, type DNSRecord, type HostedZone, type Paginated } from "@/types";

const PAGE_SIZE = 50;

export default function ZoneDetailPage() {
  const params = useParams<{ id: string }>();
  const zoneId = params.id;
  const { username, ready } = useAuth();
  const router = useRouter();
  const notify = useToast();

  const [zone, setZone] = useState<HostedZone | null>(null);
  const [zoneError, setZoneError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<DNSRecord> | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<DNSRecord | null>(null);
  const [deleting, setDeleting] = useState<DNSRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && !username) router.replace("/login");
  }, [ready, username, router]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(t);
  }, [q]);

  const loadZone = useCallback(async () => {
    try {
      const z = await api<HostedZone>(`/api/hosted-zones/${zoneId}`);
      setZone(z);
      setZoneError(null);
    } catch (err) {
      setZoneError(err instanceof ApiError ? err.message : "Failed to load hosted zone.");
    }
  }, [zoneId]);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setListError(null);
    try {
      const res = await api<Paginated<DNSRecord>>(
        `/api/hosted-zones/${zoneId}/records?q=${encodeURIComponent(debouncedQ)}&record_type=${encodeURIComponent(typeFilter)}&page=${page}&page_size=${PAGE_SIZE}`
      );
      if (res.items.length === 0 && res.page > 1) {
        // Deletions can strand the user on a now-empty page; step back instead.
        setPage(res.page - 1);
        return;
      }
      setData(res);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Failed to load records.");
    } finally {
      setLoading(false);
    }
  }, [zoneId, debouncedQ, typeFilter, page]);

  useEffect(() => {
    if (ready && username) {
      void loadZone();
      void loadRecords();
    }
  }, [ready, username, loadZone, loadRecords]);

  async function refresh() {
    await Promise.all([loadZone(), loadRecords()]);
  }

  async function handleCreate(values: RecordFormValues) {
    setBusy(true);
    setModalError(null);
    try {
      await api(`/api/hosted-zones/${zoneId}/records`, { method: "POST", body: JSON.stringify(values) });
      setShowCreate(false);
      notify({ kind: "success", title: "Record created", message: `${values.name} ${values.type}` });
      await refresh();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Create failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEdit(values: RecordFormValues) {
    if (!editing) return;
    setBusy(true);
    setModalError(null);
    try {
      await api(`/api/hosted-zones/${zoneId}/records/${editing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: values.name,
          values: values.values,
          ttl: values.ttl,
          routing_policy: values.routing_policy,
          description: values.description,
        }),
      });
      setEditing(null);
      notify({ kind: "success", title: "Record updated", message: values.name });
      await refresh();
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
      await api(`/api/hosted-zones/${zoneId}/records/${deleting.id}`, { method: "DELETE" });
      setDeleting(null);
      notify({ kind: "success", title: "Record deleted", message: `${deleting.name} ${deleting.type}` });
      await refresh();
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
        <Link href="/dashboard">Route 53</Link> &gt; <Link href="/hosted-zones">Hosted zones</Link> &gt;{" "}
        {zone ? zone.name : zoneId}
      </div>
      {zoneError ? (
        <div className="alert alert-error">
          {zoneError} <Link href="/hosted-zones">Back to hosted zones</Link>
        </div>
      ) : (
        <>
          <h1 className="page-title">{zone ? zone.name : "Loading…"}</h1>
          <p className="page-subtitle">
            {zone ? (
              <>
                {zone.id} · {zone.type} hosted zone · {zone.record_count} record(s) · Last updated{" "}
                {formatDate(zone.updated_at)}
              </>
            ) : (
              "Loading hosted zone details…"
            )}
          </p>
        </>
      )}

      {zone ? (
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-body">
            <dl className="detail-grid">
              <dt>Domain name</dt>
              <dd>{zone.name}</dd>
              <dt>Hosted zone ID</dt>
              <dd style={{ fontFamily: "Consolas, Menlo, monospace" }}>{zone.id}</dd>
              <dt>Type</dt>
              <dd>{zone.type}</dd>
              <dt>Comment</dt>
              <dd>{zone.description || "—"}</dd>
              <dt>Created</dt>
              <dd>{formatDate(zone.created_at)}</dd>
            </dl>
          </div>
        </div>
      ) : null}

      {listError ? <div className="alert alert-error">{listError}</div> : null}

      <div className="panel">
        <div className="panel-header">
          <h2>Records ({data?.total ?? 0})</h2>
          <div className="toolbar">
            <input type="search" placeholder="Search records" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search records" />
            <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }} aria-label="Filter by type">
              <option value="">All types</option>
              {RECORD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button className="btn" onClick={() => void refresh()} disabled={loading}>
              Refresh
            </button>
            <button className="btn btn-primary" onClick={() => { setModalError(null); setShowCreate(true); }}>
              Create record
            </button>
          </div>
        </div>
        <div className="panel-body flush">
          {loading ? (
            <div style={{ padding: 28 }}>
              <span className="spinner" /> Loading records…
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="empty-state">
              <h3>{debouncedQ || typeFilter ? "No records match your filters" : "No records found"}</h3>
              <p>
                {debouncedQ || typeFilter ? (
                  <button
                    className="btn-link"
                    onClick={() => {
                      setQ("");
                      setTypeFilter("");
                    }}
                  >
                    Clear search and filters
                  </button>
                ) : (
                  "Create your first record in this hosted zone."
                )}
              </p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="aws-table">
                <thead>
                  <tr>
                    <th>Record name</th>
                    <th>Type</th>
                    <th>Value(s)</th>
                    <th>TTL</th>
                    <th>Routing policy</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => {
                    const system = zone ? isSystemRecord(zone.name, r) : false;
                    return (
                    <tr key={r.id}>
                      <td style={{ fontFamily: "Consolas, Menlo, monospace", fontSize: 12.5 }}>{r.name}</td>
                      <td>
                        <span className="type-badge">{r.type}</span>{" "}
                        {system ? (
                          <span className="sys-badge" title="System-managed apex record: editable, cannot be deleted.">
                            System
                          </span>
                        ) : null}
                      </td>
                      <td>
                        <ul className="value-list">
                          {r.values.map((v, i) => (
                            <li key={i}>{v}</li>
                          ))}
                        </ul>
                      </td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {r.ttl} <span style={{ color: "#5f6b6a" }}>({formatTtl(r.ttl)})</span>
                      </td>
                      <td>{r.routing_policy}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        <button className="btn-link" onClick={() => { setEditing(r); setModalError(null); }}>
                          Edit
                        </button>
                        {" · "}
                        {system ? (
                          <span
                            className="btn-link"
                            aria-disabled="true"
                            title="Apex NS and SOA records are managed by the system and cannot be deleted."
                            style={{ color: "#879596", cursor: "not-allowed", textDecoration: "none" }}
                          >
                            Delete
                          </span>
                        ) : (
                          <button className="btn-link" onClick={() => setDeleting(r)}>
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {data && data.total > 0 ? (
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        ) : null}
      </div>

      {showCreate && zone ? (
        <RecordModal
          title={`Create record — ${zone.name}`}
          zoneName={zone.name}
          initial={{ name: "", type: "A", values: [], ttl: 300, routing_policy: "Simple", description: "" }}
          busy={busy}
          error={modalError}
          onClose={() => setShowCreate(false)}
          onSubmit={handleCreate}
        />
      ) : null}

      {editing && zone ? (
        <RecordModal
          title={`Edit record — ${editing.name}`}
          zoneName={zone.name}
          initial={{
            name: editing.name,
            type: editing.type,
            values: editing.values,
            ttl: editing.ttl,
            routing_policy: editing.routing_policy,
            description: editing.description,
          }}
          busy={busy}
          error={modalError}
          systemNotice={
            isSystemRecord(zone.name, editing)
              ? "This is a system-managed apex record. Its values and TTL can be edited, but it cannot be deleted."
              : null
          }
          onClose={() => setEditing(null)}
          onSubmit={handleEdit}
        />
      ) : null}

      {deleting ? (
        <ConfirmModal
          title={`Delete record ${deleting.name} (${deleting.type})?`}
          body={
            <p>
              This permanently deletes the <strong>{deleting.type}</strong> record for <strong>{deleting.name}</strong>.
              This action cannot be undone.
            </p>
          }
          confirmLabel="Delete record"
          busy={busy}
          onCancel={() => setDeleting(null)}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
    </AppShell>
  );
}
