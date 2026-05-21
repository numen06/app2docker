#!/usr/bin/env python3
"""One-off: replace alert()/confirm() with notify/showConfirm in frontend/src."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"

SUCCESS_KW = (
    "成功", "已删除", "已创建", "已完成", "已复制", "已保存", "已更新",
    "已启用", "已禁用", "已批准", "已拒绝", "已清理", "已加入", "已刷新",
    "已停止", "已启动", "已复制", "创建成功", "删除成功", "更新成功",
    "修改成功", "复制成功", "导入成功", "解析成功", "连接测试成功",
    "状态刷新成功",
)
ERROR_KW = (
    "失败", "错误", "无法", "不能", "请填写", "请选择", "请先", "请输入",
    "请至少", "无效", "不存在", "不能为空", "必须", "未找到", "未配置",
    "不允许", "不支持", "已存在",
)
DANGER_KW = ("删除", "禁用", "清理", "退出登录", "拒绝", "停止", "清空", "移出")

SKIP_FILES = {"AlertBanner.vue", "notify.js", "useConfirm.js", "ConfirmHost.vue", "useToast.js", "ToastHost.vue"}


def classify_message(msg: str) -> str:
    for k in SUCCESS_KW:
        if k in msg:
            return "toastSuccess"
    for k in ERROR_KW:
        if k in msg:
            return "toastError"
    if "正在" in msg or "请稍候" in msg:
        return "toastInfo"
    return "toastInfo"


def find_matching_paren(s: str, start: int) -> int:
    """start points at '(' after alert/confirm."""
    depth = 0
    i = start
    in_str = None
    escape = False
    while i < len(s):
        c = s[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == in_str:
                in_str = None
            i += 1
            continue
        if c in ("'", '"', "`"):
            in_str = c
            i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def extract_string_literal(expr: str) -> str:
    expr = expr.strip()
    m = re.match(r"^(['\"`])(.*)\1$", expr, re.DOTALL)
    if m:
        return m.group(2)
    if "+" in expr or "${" in expr or "?" in expr:
        return ""
    return expr[:80]


def replace_calls(content: str, func_name: str, replacer) -> tuple[str, int]:
    count = 0
    out = []
    i = 0
    pattern = re.compile(r"\b(window\.)?(alert|confirm)\s*\(")
    while i < len(content):
        m = pattern.search(content, i)
        if not m:
            out.append(content[i:])
            break
        out.append(content[i : m.start()])
        is_window = m.group(1) is not None
        kind = m.group(2)
        paren_start = m.end() - 1
        paren_end = find_matching_paren(content, paren_start)
        if paren_end < 0:
            out.append(content[m.start() : m.end()])
            i = m.end()
            continue
        inner = content[paren_start + 1 : paren_end]
        replacement = replacer(kind, inner, is_window)
        out.append(replacement)
        count += 1
        i = paren_end + 1
    return "".join(out), count


def replacer_factory():
    def replacer(kind: str, inner: str, is_window: bool) -> str:
        if kind == "confirm":
            msg_hint = extract_string_literal(inner.strip())
            danger = any(k in msg_hint for k in DANGER_KW)
            danger_part = ", danger: true" if danger else ""
            return f"showConfirm({{ message: {inner.strip()}{danger_part} }})"
        fn = classify_message(extract_string_literal(inner.strip()))
        return f"{fn}({inner.strip()})"

    return replacer


def fix_confirm_await(content: str) -> str:
    """Wrap showConfirm in await for common patterns."""
    content = re.sub(
        r"if\s*\(\s*!\s*showConfirm\(",
        "if (!(await showConfirm(",
        content,
    )
    content = re.sub(
        r"if\s*\(\s*showConfirm\(",
        "if (await showConfirm(",
        content,
    )
    content = re.sub(
        r"!\s*showConfirm\(",
        "!(await showConfirm(",
        content,
    )
    content = re.sub(
        r"const\s+(\w+)\s*=\s*showConfirm\(",
        r"const \1 = await showConfirm(",
        content,
    )
    content = re.sub(
        r"const\s+(\w+)\s*=\s*await\s+await\s+showConfirm",
        r"const \1 = await showConfirm",
        content,
    )
    return content


def ensure_imports(content: str, path: Path) -> str:
    needs_notify = any(
        x in content
        for x in ("toastSuccess(", "toastError(", "toastInfo(", "toastApiError(")
    )
    needs_confirm = "showConfirm(" in content
    if not needs_notify and not needs_confirm:
        return content

    notify_import = 'import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";'
    confirm_import = 'import { showConfirm } from "@/composables/useConfirm";'

    imports = []
    if needs_notify and notify_import not in content:
        imports.append(notify_import)
    if needs_confirm and confirm_import not in content:
        imports.append(confirm_import)

    if not imports:
        return content

    block = "\n".join(imports) + "\n"

    if "<script setup>" in content:
        content = content.replace("<script setup>", "<script setup>\n" + block, 1)
    elif re.search(r"<script[^>]*setup[^>]*>", content):
        m = re.search(r"(<script[^>]*setup[^>]*>)", content)
        if m:
            content = content[: m.end()] + "\n" + block + content[m.end() :]
    elif re.search(r"export default\s*\{", content):
        # options API - add after first import or at script start
        sm = re.search(r"<script>", content)
        if sm:
            content = content.replace("<script>", "<script>\n" + block, 1)
    else:
        # plain .js
        if content.startswith("import "):
            first_nl = content.find("\n")
            content = content[: first_nl + 1] + block + content[first_nl + 1 :]
        else:
            content = block + content

    return content


def process_file(path: Path) -> tuple[int, int]:
    if path.name in SKIP_FILES:
        return 0, 0
    text = path.read_text(encoding="utf-8")
    if "alert(" not in text and "confirm(" not in text and "window.confirm" not in text:
        return 0, 0
    new_text, n = replace_calls(text, "alert", replacer_factory())
    new_text = fix_confirm_await(new_text)
    new_text = ensure_imports(new_text, path)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return n, n


def main():
    total = 0
    for ext in ("*.vue", "*.js"):
        for path in ROOT.rglob(ext):
            if "node_modules" in str(path):
                continue
            c, _ = process_file(path)
            if c:
                print(f"{path.relative_to(ROOT.parent)}: {c}")
                total += c
    print(f"total replacements: {total}")


if __name__ == "__main__":
    main()
