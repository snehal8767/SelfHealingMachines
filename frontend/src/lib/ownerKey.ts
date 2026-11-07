/**
 * Owner key storage.
 *
 * The key is entered by the owner in the browser and kept in localStorage.
 * It is deliberately NOT baked into the bundle via VITE_*: anything in a Vite
 * bundle is public, so a build-time token would let any visitor mutate data.
 */
const STORAGE_KEY = "shm.owner-key.v1";

export function getOwnerKey(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setOwnerKey(value: string): void {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode / storage disabled — the UI simply stays locked */
  }
}
