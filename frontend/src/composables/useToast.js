import { ref } from "vue";

const MAX_TOASTS = 3;
const toasts = ref([]);
let idSeq = 0;
const timers = new Map();

/**
 * @param {{ message: string, variant?: 'success'|'error'|'info', duration?: number }} opts
 */
export function showToast({ message, variant = "info", duration = 6000 }) {
  const id = ++idSeq;
  const entry = { id, message, variant };
  const next = [...toasts.value, entry];
  if (next.length > MAX_TOASTS) {
    const removed = next.shift();
    const t = timers.get(removed.id);
    if (t) {
      clearTimeout(t);
      timers.delete(removed.id);
    }
  }
  toasts.value = next;
  if (duration > 0) {
    const timer = setTimeout(() => dismissToast(id), duration);
    timers.set(id, timer);
  }
  return id;
}

export function dismissToast(id) {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
  toasts.value = toasts.value.filter((t) => t.id !== id);
}

export function useToast() {
  return { toasts, showToast, dismissToast };
}
