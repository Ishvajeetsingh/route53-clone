export interface HostedZone {
  id: string;
  name: string;
  description: string;
  type: string;
  record_count: number;
  created_at: string;
  updated_at: string;
}

export interface DNSRecord {
  id: number;
  zone_id: string;
  name: string;
  type: string;
  values: string[];
  ttl: number;
  routing_policy: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const RECORD_TYPES = ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA", "SOA"] as const;
export const ROUTING_POLICIES = ["Simple", "Weighted", "Latency", "Failover", "Geolocation"] as const;
