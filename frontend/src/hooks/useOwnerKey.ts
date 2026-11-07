import { useCallback, useEffect, useState } from "react";
import { getOwnerKey, setOwnerKey } from "../lib/ownerKey";

const EVENT = "shm:owner-key-changed";

/**
 * Shared owner-key state. Every consumer re-renders when the key changes,
 * so disabling write buttons in one place updates the whole dashboard.
 */
export function useOwnerKey() {
  const [key, setKey] = useState<string>(getOwnerKey);

  useEffect(() => {
    const sync = () => setKey(getOwnerKey());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const update = useCallback((value: string) => {
    setOwnerKey(value);
    window.dispatchEvent(new Event(EVENT));
  }, []);

  return { key, unlocked: key.length > 0, update };
}
