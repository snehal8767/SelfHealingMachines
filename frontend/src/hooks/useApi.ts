import { useEffect, useState } from "react";

interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Minimal fetch hook: loading / error / data + a reload counter so actions
 * (resolve an order, finish a retrain) can force a refetch.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    fetcher()
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((err: unknown) => {
        if (!live) return;
        const message = err instanceof Error ? err.message : "Unknown error";
        setState({ data: null, error: message, loading: false });
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { ...state, reload: () => setTick((value) => value + 1) };
}
