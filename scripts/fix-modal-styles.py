#!/usr/bin/env python3
"""统一修复弹窗：关闭按钮、重复 backdrop、遮罩层 class。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"

FILES = [
    "PipelinePanel.vue",
    "StepBuildPanel.vue",
    "DataSourcePanel.vue",
    "BuildConfigEditor.vue",
    "AgentHostManager.vue",
]


def fix_close_buttons(text: str) -> str:
    text = re.sub(
        r'(<button\b[^>]*@click="[^"]*"[^>]*)\s*>\s*</Button>',
        r'\1><i class="fas fa-times"></i></button>',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(<button\b[^>]*)\s*>\s*</Button>',
        r'\1><i class="fas fa-times"></i></button>',
        text,
        flags=re.IGNORECASE,
    )
    return text


def fix_backdrops(text: str) -> str:
    return re.sub(
        r"\n\s*<div\s+v-if=\"[^\"]+\"\s+class=\"modal-backdrop fade show\"[^>]*>\s*</div>\s*",
        "\n",
        text,
    )


def fix_overlay(text: str) -> str:
    text = re.sub(
        r'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"(?:\s+style="[^"]*")?(?:\s+tabindex="[^"]*")?',
        'class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"',
        text,
    )

    def add_click_self(m):
        block = m.group(0)
        if "@click.self" in block or "@click=" in block:
            return block
        return block[:-1] + ' @click.self>'

    text = re.sub(
        r'<div\s+v-if="[^"]+"\s+class="fixed inset-0 z-\[2000\][^>]*>',
        add_click_self,
        text,
    )
    return text


def fix_modal_dialog_wrapper(text: str) -> str:
    replacements = {
        'class="modal-dialog modal-lg modal-dialog-scrollable"': 'class="relative z-10 w-full max-w-3xl"',
        'class="modal-dialog modal-xl modal-dialog-scrollable"': 'class="relative z-10 w-full max-w-5xl"',
        'class="modal-dialog modal-dialog-scrollable"': 'class="relative z-10 w-full max-w-lg"',
        'class="modal-dialog modal-dialog-centered"': 'class="relative z-10 mx-auto w-full max-w-md"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def add_overlay_backdrop_div(text: str) -> str:
    """在仅有一层 fixed 的弹窗外层内补上独立遮罩（若尚未有 absolute inset-0）。"""

    def patch(m):
        inner = m.group(1)
        if "absolute inset-0 bg-black/50" in inner[:400]:
            return m.group(0)
        return (
            m.group(0).split(">", 1)[0]
            + ">"
            + '\n      <div class="absolute inset-0 bg-black/50" aria-hidden="true"></div>'
            + inner
        )

    return re.sub(
        r'(<div\s+v-if="[^"]+"\s+class="fixed inset-0 z-\[2000\][^>]*>)([\s\S]*?)(?=\n\s*<div\s+class="(?:relative z-10|my-8))',
        patch,
        text,
        count=0,
    )


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    text = fix_backdrops(text)
    text = fix_overlay(text)
    text = fix_close_buttons(text)
    text = fix_modal_dialog_wrapper(text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    changed = []
    for name in FILES:
        p = ROOT / name
        if p.exists() and process_file(p):
            changed.append(name)
    print("Updated:", ", ".join(changed) or "(none)")


if __name__ == "__main__":
    main()
