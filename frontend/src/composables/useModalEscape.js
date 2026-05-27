import { onMounted, onUnmounted } from "vue";

export function useModalEscape() {
  function handleEscape(event) {
    if (event.key !== "Escape") return;

    const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
    const visibleDialogs = dialogs.filter((dialog) => {
      const style = window.getComputedStyle(dialog);
      return style.display !== "none" && style.visibility !== "hidden";
    });

    const topDialog = visibleDialogs.at(-1);
    const closeButton = topDialog?.querySelector('[aria-label="关闭"], [data-dialog-close]');
    closeButton?.click();
  }

  onMounted(() => {
    window.addEventListener("keydown", handleEscape);
  });

  onUnmounted(() => {
    window.removeEventListener("keydown", handleEscape);
  });
}
