import { useEffect, useState } from "react";
import api from "../services/api";
import { errorMessage } from "./errors";
import { cleanParams, readPage } from "./paging";

export function usePaged<T>(path: string, params: Record<string, string | undefined> = {}, enabled = true) {
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const [rows, setRows] = useState<T[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(enabled);
  const serialized = JSON.stringify(params);

  useEffect(() => {
    setPage(1);
  }, [serialized, path]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancel = false;
    setLoading(true);
    api
      .get(path, { params: { ...cleanParams(JSON.parse(serialized) as Record<string, string>), page } })
      .then((response) => {
        if (cancel) return;
        const parsed = readPage<T>(response.data);
        setRows(parsed.results);
        setCount(parsed.count);
        setError("");
      })
      .catch((reason) => {
        if (cancel) return;
        setRows([]);
        setCount(0);
        setError(errorMessage(reason, "Could not load this list."));
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [path, serialized, page, tick, enabled]);

  return {
    rows,
    count,
    error,
    loading,
    page,
    setPage,
    reload: () => setTick((current) => current + 1),
  };
}
