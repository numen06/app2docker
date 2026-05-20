/**
 * 从粘贴内容或 URL 中提取团队邀请 token。
 */
export function extractInviteToken(raw) {
  const s = (raw || "").trim();
  if (!s) return "";

  try {
    const url = new URL(s, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    const fromQuery = url.searchParams.get("invite");
    if (fromQuery && fromQuery.trim()) return fromQuery.trim();
    const pathMatch = url.pathname.match(/\/invitations\/([^/?#]+)/i);
    if (pathMatch) return pathMatch[1];
  } catch {
    /* 非 URL，继续按纯文本处理 */
  }

  const inlineMatch = s.match(/invitations\/([^/?#]+)/i);
  if (inlineMatch) return inlineMatch[1];

  const queryMatch = s.match(/[?&]invite=([^&#]+)/i);
  if (queryMatch) {
    try {
      return decodeURIComponent(queryMatch[1]).trim();
    } catch {
      return queryMatch[1].trim();
    }
  }

  return s;
}

/** 生成可分享的团队邀请链接（登录后打开 /onboarding 接受邀请） */
export function buildTeamInviteLink(token) {
  const t = (token || "").trim();
  if (!t) return "";
  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "";
  const base = import.meta.env.BASE_URL || "/";
  const path = `${base.replace(/\/$/, "")}/onboarding`.replace(/^\/\//, "/");
  const url = new URL(path, origin || "http://localhost");
  url.searchParams.set("invite", t);
  return url.toString();
}

export function formatInviteExpiresAt(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(iso);
  }
}
