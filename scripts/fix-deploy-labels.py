#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix Label/label mismatches and add component registration."""
import re
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "DeployTaskManager.vue"

COMPONENTS_IMPORTS = """import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import { Badge } from "@/components/ui/badge";
import Table from "@/components/ui/table/Table.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
"""

COMPONENTS_REG = """  components: {
    PageToolbar,
    PaginationBar,
    EmptyState,
    AlertBanner,
    Button,
    Input,
    Label,
    NativeSelect,
    FormDialog,
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
  },
"""

RADIO_LABEL_TW = (
    "cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm "
    "hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
)
TEXTAREA_CLS = (
    "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono "
    "shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
)


def main():
    text = TARGET.read_text(encoding="utf-8")

    # Radio/checkbox host labels: </Label> after <label ... for=
    text = re.sub(
        r"(<label\b[^>]*for=[^>]*>[\s\S]*?)</Label>",
        r"\1</label>",
        text,
    )
    # flex-fill tab buttons in edit mode
    text = re.sub(
        r"(<label\b[^>]*class=\"[^\"]*flex-fill[^\"]*\"[^>]*>[\s\S]*?)</Label>",
        r"\1</label>",
        text,
    )

    # Remove stray > after <Label>
    text = re.sub(r"<Label>\s*>\s*", "<Label>", text)
    text = re.sub(r"<Label class=\"([^\"]+)\">\s*>\s*", r'<Label class="\1">', text)

    # form-label -> Label
    text = re.sub(
        r'<label class="form-label([^"]*)"([^>]*)>',
        lambda m: f'<Label class="text-sm font-medium{m.group(1)}"{m.group(2)}>',
        text,
    )
    text = re.sub(r'<label class="form-label"', "<Label", text)

    # btn radio labels tailwind
    text = re.sub(
        r'<label(\s+[^>]*?)class="btn btn-outline-[^"]*"',
        rf'<label\1class="{RADIO_LABEL_TW}"',
        text,
    )
    text = re.sub(
        r'<label(\s+[^>]*?)class="btn btn-outline-primary flex-fill"',
        rf'<label\1class="{RADIO_LABEL_TW} flex-1 text-center"',
        text,
    )

    # spinners in buttons
    text = re.sub(
        r"<span\s+class=\"spinner-border[^\"]*\"\s*></span\s*>",
        '<i class="fas fa-spinner fa-spin mr-2"></i>',
        text,
    )
    text = re.sub(
        r'<span\s+class=\"spinner-border[^\"]*\"\s*></span',
        '<i class="fas fa-spinner fa-spin mr-2"></i>',
        text,
    )

    text = text.replace('class="form-control font-mono form-control-sm"', f'class="{TEXTAREA_CLS} text-xs"')
    text = text.replace('class="invalid-feedback block"', 'class="mt-1 block text-xs text-red-500"')

    if "components:" not in text:
        text = text.replace(
            'import { copyToClipboard } from "../utils/clipboard.js";',
            'import { copyToClipboard } from "../utils/clipboard.js";\n' + COMPONENTS_IMPORTS,
        )
        text = text.replace(
            '  name: "DeployTaskManager",\n  data()',
            '  name: "DeployTaskManager",\n' + COMPONENTS_REG + "  data()",
        )

    TARGET.write_text(text, encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
