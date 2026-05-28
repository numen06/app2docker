import { showToast } from "@/composables/useToast";

export function toastSuccess(message, duration = 6000) {
  return showToast({ message, variant:"success", duration });
}

export function toastError(message, duration = 8000) {
  return showToast({ message, variant:"error", duration });
}

export function toastInfo(message, duration = 6000) {
  return showToast({ message, variant:"info", duration });
}

/**
 * @param {unknown} err
 * @param {string} [fallback]
 */
export function toastApiError(err, fallback ="操作失败") {
  const detail =
    err?.response?.data?.detail ?? err?.response?.data?.error ?? err?.message ?? fallback;
  const message = typeof detail ==="string" ? detail : String(detail ?? fallback);
  return toastError(message);
}
