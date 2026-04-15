/**
 * 统一的剪贴板复制工具函数
 *
 * 优先使用 navigator.clipboard API，失败时自动降级到 execCommand。
 * 在非 HTTPS 环境下 clipboard API 可能不可用，execCommand 仍可正常工作。
 */

function fallbackCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '-9999px'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  textarea.setSelectionRange(0, text.length)
  let success = false
  try {
    success = document.execCommand('copy')
  } catch (e) {
    success = false
  }
  document.body.removeChild(textarea)
  return success
}

export async function copyToClipboard(text) {
  if (!text) return false

  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn('Clipboard API 失败，尝试降级方案:', err)
      return fallbackCopy(text)
    }
  }

  return fallbackCopy(text)
}
