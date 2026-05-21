import { ref } from "vue";

/** @type {import('vue').Ref<null | { id: number, title: string, message: string, confirmText: string, cancelText: string, danger: boolean, resolve: (ok: boolean) => void }>} */
const pending = ref(null);
let idSeq = 0;

/**
 * @param {{ message: string, title?: string, confirmText?: string, cancelText?: string, danger?: boolean }} opts
 * @returns {Promise<boolean>}
 */
export function showConfirm({
  message,
  title = "确认",
  confirmText = "确定",
  cancelText = "取消",
  danger = false,
}) {
  return new Promise((resolve) => {
    const id = ++idSeq;
    pending.value = {
      id,
      title,
      message,
      confirmText,
      cancelText,
      danger,
      resolve,
    };
  });
}

export function resolveConfirm(ok) {
  const current = pending.value;
  if (!current) return;
  pending.value = null;
  current.resolve(ok);
}

export function useConfirm() {
  return { pending, showConfirm, resolveConfirm };
}
