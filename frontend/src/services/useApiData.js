import { useEffect, useReducer, useState } from "react";
import { apiRequest } from "./api.js";

export function useApiData(path, token) {
  const [revision, reload] = useReducer((value) => value + 1, 0);
  const [result, setResult] = useState(null);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    const key = { path, token, revision };
    apiRequest(path, { token, signal: controller.signal }).then(
      (data) => { if (!controller.signal.aborted) setResult({ ...key, data }); },
      (error) => { if (!controller.signal.aborted) setResult({ ...key, error }); }
    );
    return () => controller.abort();
  }, [path, token, revision]);

  const current = result?.path === path && result?.token === token && result?.revision === revision;
  const data = current ? result.data : null;
  return { data, rows: Array.isArray(data) ? data : data?.results ?? [],
    loading: Boolean(path) && !current, error: current ? result.error : null, reload };
}
