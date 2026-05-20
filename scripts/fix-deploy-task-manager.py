#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

TEXTAREA_CLS = (
    "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono "
    "shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
)

RADIO_LABEL_TW = (
    "cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm "
    "hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
)


def main():
    text = TARGET.read_text(encoding="utf-8")

    # root wrapper
    if not text.startswith("<template>\n  <div>"):
        text = text.replace("<template>\n    <PageToolbar", "<template>\n  <div>\n    <PageToolbar", 1)
        text = text.replace("\n</template>", "\n  </div>\n</template>", 1)

    # Fix broken Label tags from bad replace
    text = re.sub(r"<Label\s*\"", "<Label>", text)
    text = re.sub(r'<Label\s+small\s*">', '<Label class="text-xs">', text)
    text = re.sub(r'<Label\s+small\s+mb-1\s*">', '<Label class="mb-1 text-xs">', text)
    text = re.sub(r"</label\s*>", "</Label>", text, flags=re.I)
    text = re.sub(r"</label\s*\n", "</Label>\n", text, flags=re.I)

    # spinners
    text = re.sub(
        r'<span\s+class="spinner-border(?:\s+spinner-border-sm)?[^"]*"\s*></span>',
        '<i class="fas fa-spinner fa-spin"></i>',
        text,
    )
    text = re.sub(
        r'<span\s+v-if="creating"\s+class="spinner-border[^"]*"\s*></span>',
        '<i v-if="creating" class="fas fa-spinner fa-spin mr-2"></i>',
        text,
    )

    # textarea form-control
    text = text.replace('class="form-control font-mono"', f'class="{TEXTAREA_CLS}"')
    text = re.sub(r'class="form-control(?:\s+form-control-sm)?"', f'class="{TEXTAREA_CLS}"', text)

    # radio labels (btn btn-outline-*)
    text = re.sub(
        r'<label class="btn btn-outline-(\w+)"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )
    text = re.sub(
        r'<label\s+class="btn btn-outline-(\w+)"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )
    text = re.sub(
        r'<label\s+class="btn btn-outline-success"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )
    text = re.sub(
        r'<label\s+class="btn btn-outline-info"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )
    text = re.sub(
        r'<label\s+class="btn btn-outline-warning"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )

    # filter radio labels
    text = re.sub(
        r'<label class="btn btn-outline-secondary"',
        f'<label class="{RADIO_LABEL_TW}"',
        text,
    )

    # remaining badge bg-
    text = text.replace('class="badge bg-primary mr-2"', 'class="mr-2"')
    text = text.replace('class="badge bg-info ml-1"', 'variant="info" class="ml-1"')
    text = re.sub(
        r'<span class="badge bg-info ml-1">',
        '<Badge variant="info" class="ml-1">',
        text,
    )
    text = re.sub(
        r'<span\s+:class="getStatusBadgeClass\(([^)]+)\)"\s+class="badge ml-1"\s*>',
        r'<Badge :variant="\1 === \'completed\' ? \'success\' : \1 === \'failed\' ? \'danger\' : \1 === \'running\' ? \'info\' : \'default\'" class="ml-1">',
        text,
    )
    # fix span badges that should be Badge
    text = re.sub(
        r'<span class="badge bg-primary mr-2">',
        '<Badge variant="default" class="mr-2">',
        text,
    )

    # btn-group -> flex
    text = re.sub(r'class="btn-group w-100"', 'class="flex w-full flex-wrap gap-2"', text)
    text = re.sub(r'class="btn-group"', 'class="inline-flex flex-wrap gap-1"', text)

    # script components
    if "PageToolbar" not in text:
        text = text.replace(
            'import { copyToClipboard } from "../utils/clipboard.js";',
            'import { copyToClipboard } from "../utils/clipboard.js";\n' + COMPONENTS_IMPORTS,
        )
        text = text.replace(
            '  name: "DeployTaskManager",\n  data()',
            '  name: "DeployTaskManager",\n' + COMPONENTS_REG + "  data()",
        )

    # empty style
    text = re.sub(r"<style scoped>.*?</style>", "<style scoped>\n</style>", text, flags=re.DOTALL)

    TARGET.write_text(text, encoding="utf-8")
    print("fixed", TARGET)


if __name__ == "__main__":
    main()
