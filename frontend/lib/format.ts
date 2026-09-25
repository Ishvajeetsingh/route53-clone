const HAS_OFFSET = /(Z|[+-]\d{2}:?\d{2})$/;

/**
 * Single shared datetime formatter. The API emits UTC ISO-8601 with an
 * explicit offset; offset-less strings (legacy payloads) are UTC by
 * convention. Rendering uses the browser's local timezone.
 */
export function formatDate(iso: string): string {
  const normalized = HAS_OFFSET.test(iso.trim()) ? iso : `${iso.trim()}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTtl(ttl: number): string {
  if (ttl >= 86400 && ttl % 86400 === 0) return `${ttl / 86400}d`;
  if (ttl >= 3600 && ttl % 3600 === 0) return `${ttl / 3600}h`;
  if (ttl >= 60 && ttl % 60 === 0) return `${ttl / 60}m`;
  return `${ttl}s`;
}

const PLACEHOLDERS: Record<string, string> = {
  A: "192.0.2.1",
  AAAA: "2001:db8::1",
  CNAME: "target.example.com.",
  TXT: '"v=spf1 include:_spf.example.com ~all"',
  MX: "10 mail.example.com.",
  NS: "ns-1.awsdns-1.com.",
  PTR: "host.example.com.",
  SRV: "10 5 443 target.example.com.",
  CAA: '0 issue "ca.example.com"',
  SOA: "ns-1.awsdns-1.com. hostmaster.example.com. 1 7200 900 1209600 86400",
};

export function placeholderFor(type: string): string {
  return PLACEHOLDERS[type] ?? "value";
}

const HINTS: Record<string, string> = {
  A: "One IPv4 address per line, e.g. 192.0.2.1",
  AAAA: "One IPv6 address per line, e.g. 2001:db8::1",
  CNAME: "Exactly one hostname target.",
  TXT: "One quoted string per line.",
  MX: "Priority + mail host per line, e.g. 10 mail.example.com.",
  NS: "One name server hostname per line.",
  PTR: "One canonical hostname.",
  SRV: "Priority weight port target, e.g. 10 5 443 sip.example.com.",
  CAA: 'Flags tag value, e.g. 0 issue "ca.example.com"',
  SOA: "Managed automatically; edit with care.",
};

export function hintFor(type: string): string {
  return HINTS[type] ?? "";
}

function apexKey(name: string): string {
  return name.replace(/\.+$/, "").toLowerCase();
}

/** Apex NS/SOA records are system-managed: editable, never deletable. Mirrors the backend rule. */
export function isSystemRecord(zoneName: string, record: { name: string; type: string }): boolean {
  return (
    (record.type === "NS" || record.type === "SOA") && apexKey(record.name) === apexKey(zoneName)
  );
}
