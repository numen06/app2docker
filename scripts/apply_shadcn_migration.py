#!/usr/bin/env python3
"""Generate migrated Vue templates for Bootstrap -> shadcn/ui (template + imports only)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend" / "src" / "components"

IMPORTS = {
    "BuildConfigEditor": """
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
""",
    "DockerManager": """
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import { Badge } from "@/components/ui/badge";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
""",
    "DataSourcePanel": """
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import { Badge } from "@/components/ui/badge";
""",
    "HostManager": """
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import { Badge } from "@/components/ui/badge";
""",
}

HOST_COMPONENTS = """
  components: {
    FormDialog,
    EmptyState,
    AlertBanner,
    Button,
    Input,
    Label,
    Card,
    CardHeader,
    CardTitle,
    CardContent,
    Badge,
  },
"""


def git_show(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{path}"], cwd=ROOT, text=True, encoding="utf-8"
    )


def split_vue(text: str):
    m = re.search(r"<template>(.*?)</template>\s*(<script[^>]*>.*?</script>)\s*(<style[^>]*>.*?</style>)?", text, re.DOTALL)
    if not m:
        raise ValueError("invalid vue")
    return m.group(1), m.group(2), m.group(3) or ""


def util_migrate(tpl: str) -> str:
    from migrate_vue_bootstrap import migrate_template  # type: ignore

    return migrate_template(tpl)


def strip_scoped_style(script_style: str) -> str:
    return re.sub(r"\n<style scoped>.*?</style>\s*$", "\n", script_style, flags=re.DOTALL)


def inject_imports(script: str, name: str, options_api: bool = False) -> str:
    block = IMPORTS[name].strip()
    if options_api:
        script = script.replace(
            "export default {",
            f"import FormDialog from '@/components/ui/dialog/FormDialog.vue';\n"
            f"import EmptyState from '@/components/ui/EmptyState.vue';\n"
            f"import AlertBanner from '@/components/ui/AlertBanner.vue';\n"
            f"import Button from '@/components/ui/button/Button.vue';\n"
            f"import Input from '@/components/ui/input/Input.vue';\n"
            f"import Label from '@/components/ui/label/Label.vue';\n"
            f"import Card from '@/components/ui/card/Card.vue';\n"
            f"import CardHeader from '@/components/ui/card/CardHeader.vue';\n"
            f"import CardTitle from '@/components/ui/card/CardTitle.vue';\n"
            f"import CardContent from '@/components/ui/card/CardContent.vue';\n"
            f"import {{ Badge }} from '@/components/ui/badge';\n\nexport default {{",
            1,
        )
        script = script.replace("  name: 'HostManager',", "  name: 'HostManager'," + HOST_COMPONENTS, 1)
        return script
    if "import axios" in script:
        return script.replace("import axios", block + "\nimport axios", 1)
    return block + "\n" + script


def main():
    print("Run per-file migrations manually - this script provides helpers only")


if __name__ == "__main__":
    main()
