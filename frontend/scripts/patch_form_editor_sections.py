from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src/components/pipeline/PipelineFormEditor.vue"
t = p.read_text(encoding="utf-8")

marker = "                </motion>\n\n                <!-- Dockerfile & 镜像配置 Tab -->"
marker = marker.replace("motion", "div")
insert = """                </motion>

                <PipelineMultiServiceTab
                  v-if="section === 'services'"
                  embedded
                />

                <!-- Dockerfile & 镜像配置 Tab -->"""
insert = insert.replace("motion", "div")

if marker not in t:
    raise SystemExit("services marker missing")
t = t.replace(marker, insert, 1)

wh_marker = """                  id="webhook-pane"
                >
                  <div class="mb-3">"""
wh_insert = """                  id="webhook-pane"
                >
                  <PipelineWebhookUrlBlock :webhook-token="formData.webhook_token" />
                  <div class="mb-3">"""
if wh_marker not in t:
    raise SystemExit("webhook marker missing")
t = t.replace(wh_marker, wh_insert, 1)

p.write_text(t, encoding="utf-8")
print("ok")
