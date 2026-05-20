#!/usr/bin/env python3
"""Batch shadcn component replacements on Vue templates."""
import re
import sys
from pathlib import Path

REPLACEMENTS = [
    # BuildConfigEditor / generic
    (r'<div class="card">\s*<div class="card-body">', "<Card><CardContent class=\"p-4\">"),
    (r'</motionless-host-manager />\s*</motionless-host-manager />', "</CardContent></Card>"),
    (r'</div>\s*</motionless-host-manager />', "</CardContent></Card>"),
    (r'class="form-label"', 'class="text-sm font-medium text-slate-700"'),
    (r'<label class="text-sm font-medium text-slate-700">', "<Label>"),
    (r'</label>\s*<input\s+v-model="([^"]+)"\s+type="text"\s+class="form-control form-control-sm"\s*([^>]*)>',
     r'<Label>\1</Label>\n              <Input v-model="\1" type="text" \2>'),
]

# Simpler: per-file handlers
def migrate_build_config(path: Path):
    text = path.read_text(encoding="utf-8")
    # card
    text = text.replace(
        '    <div class="card">\n      <div class="card-body">',
        "    <Card>\n      <CardContent class=\"p-4\">",
        1,
    )
  # find closing of card - before JSON modal
    text = text.replace(
        "      </div>\n    </div>\n\n    <!-- JSON模态框 -->",
        "      </CardContent>\n    </Card>\n\n    <!-- JSON模态框 -->",
        1,
    )
    # JSON modal -> FormDialog
    old_modal = re.search(
        r"    <!-- JSON模态框 -->.*?</div>\s*<div v-if=\"showJsonModal\" class=\"modal-backdrop.*?</div>\s*",
        text,
        re.DOTALL,
    )
    if old_modal:
        new_modal = """    <FormDialog v-model="showJsonModal" title="构建配置 JSON" icon="fa-code" size="lg">
      <motionless-host-manager />
      <template #footer>
        <Button variant="outline" type="button" @click="showJsonModal = false">关闭</Button>
      </template>
    </FormDialog>
"""
        text = text[: old_modal.start()] + new_modal + text[old_modal.end() :]

    path.write_text(text, encoding="utf-8")
    print("patched", path)


if __name__ == "__main__":
    migrate_build_config(Path(sys.argv[1]))
