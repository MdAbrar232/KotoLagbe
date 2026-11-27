import { useEffect, useReducer, useState } from "react";
import { transportRequest } from "./api.js";

export function useTransportList(path) {
  const [revision, reload] = useReducer((n) => n + 1, 0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    async function load() {
      try {
        const rows = await transportRequest(path, { signal: controller.signal });
        if (!Array.isArray(rows)) throw new Error("The transport service returned an unexpected list.");
        if (!controller.signal.aborted) setResult({ path, revision, rows });
      } catch (error) {
        if (!controller.signal.aborted) setResult({ path, revision, error });
      }
    }
    load();
    return () => controller.abort();
  }, [path, revision]);

  const current = result?.path === path && result?.revision === revision;
  return {
    loading: Boolean(path) && !current,
    rows: current ? result.rows ?? [] : [],
    error: current ? result.error : null,
    reload,
  };
}
