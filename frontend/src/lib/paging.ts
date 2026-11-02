import api from "../services/api";

export const PAGE_SIZE = 25;

export type PageResult<T> = {
  count: number;
  results: T[];
  hasNext: boolean;
  hasPrevious: boolean;
};

export function readPage<T>(data: unknown): PageResult<T> {
  if (Array.isArray(data)) {
    return { count: data.length, results: data as T[], hasNext: false, hasPrevious: false };
  }
  const body = (data ?? {}) as { count?: number; next?: string | null; previous?: string | null; results?: T[] };
  const results = body.results ?? [];
  return {
    count: body.count ?? results.length,
    results,
    hasNext: Boolean(body.next),
    hasPrevious: Boolean(body.previous),
  };
}

export async function fetchAll<T>(path: string, params: Record<string, string | number | undefined> = {}) {
  const rows: T[] = [];
  let page = 1;
  let count = 0;
  for (let i = 0; i < 8; i += 1) {
    const response = await api.get(path, { params: { ...cleanParams(params), page } });
    const parsed = readPage<T>(response.data);
    count = parsed.count;
    rows.push(...parsed.results);
    if (!parsed.hasNext) return { rows, count, truncated: false };
    page += 1;
  }
  return { rows, count, truncated: rows.length < count };
}

export function cleanParams(params: Record<string, string | number | undefined>) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined && value !== ""));
}
