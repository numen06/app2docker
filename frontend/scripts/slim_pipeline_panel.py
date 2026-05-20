from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "src/components/PipelinePanel.vue"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

def idx(sub, start=0):
    for i in range(start, len(lines)):
        if sub in lines[i]:
            return i
    raise ValueError(sub)

webhook = idx("<!-- Webhook URL 模态框 -->")
manual = idx("<!-- 手动触发分支选择模态框 -->")
log_m = idx("<!-- 日志查看模态框 -->")
history = idx("<!-- 历史构建模态框 -->")
json_m = idx("<!-- 通过JSON创建流水线模态框 -->")
perm = idx("<ResourceMemberPermissionDialog")

out = []
out.extend(lines[:webhook])
out.extend(lines[manual:history])
out.extend(lines[json_m:perm])
# closing template div + script
out.extend(["  </div>\n", "</template>\n"])
script_start = idx("<script setup>")
out.extend(lines[script_start:])

text = "".join(out)

text = re.sub(
    r'@click="showHistory\(pipeline\)"[^/]*/>\s*</Button>\s*',
    "",
    text,
)
for fn in [
    "showWebhookUrl",
    "goToEdit",
    "openResourcePermission",
    "showMultiServiceConfig",
]:
    text = re.sub(
        rf'<Button[^>]*@click="{fn}\(pipeline\)"[^>]*>.*?</Button>\s*',
        "",
        text,
        flags=re.DOTALL,
    )

if "goToDetail" not in text:
    text = text.replace(
        """              </Button>
            </motion>""".replace("motion", "div"),
        """              </Button>
              <Button
                variant="outline" size="sm"
                @click="goToDetail(pipeline)"
                title="管理流水线"
              >
                <i class="fas fa-cog"></i> 管理
              </Button>
            </div>""",
        1,
    )
    text = text.replace(
        """              </Button>
            </div>""",
        """              </Button>
              <Button
                variant="outline" size="sm"
                @click="goToDetail(pipeline)"
                title="管理流水线"
              >
                <i class="fas fa-cog"></i> 管理
              </Button>
            </motion>""".replace("</motion>", "</motion>").replace("motion", "motion"),
        1,
    )

text = text.replace(
    '<strong class="break-words">{{ pipeline.name }}</strong>',
    '<strong class="break-words cursor-pointer text-blue-600 hover:underline" @click="goToDetail(pipeline)">{{ pipeline.name }}</strong>',
)

text = re.sub(
    r"\s*<DropdownMenuItem[^>]*deletePipeline.*?</DropdownMenuItem>\s*",
    "\n",
    text,
    flags=re.DOTALL,
)

path.write_text(text, encoding="utf-8")
print("done", len(text.splitlines()))
