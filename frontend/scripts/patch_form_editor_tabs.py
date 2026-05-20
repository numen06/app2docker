from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "src/components/pipeline/PipelineFormEditor.vue"
t = p.read_text(encoding="utf-8")
t = re.sub(
    r"              <!-- Tab 导航 -->.*?              <!-- Tab 内容 -->\n",
    "              <!-- Tab 内容 -->\n",
    t,
    flags=re.S,
)
for key in [
    "basic",
    "git",
    "build",
    "dockerfile",
    "resource",
    "webhook",
    "post_webhook",
    "other",
]:
    old = (
        'class="tab-pane fade"\n'
        f'                  :class="{{ \'show active\': activeTab === \'{key}\' }}"'
    )
    new = f'v-if="section === \'{key}\'"\n                  class="tab-pane"'
    t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("ok")
