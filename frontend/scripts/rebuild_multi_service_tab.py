from pathlib import Path
import re

body_path = (
    Path(__file__).resolve().parents[1]
    / "src/components/pipeline/detail/_multi_service_body.txt"
)
out_path = (
    Path(__file__).resolve().parents[1]
    / "src/components/pipeline/detail/PipelineMultiServiceTab.vue"
)

body = body_path.read_text(encoding="utf-8")
body = re.sub(r"^.*<div class=\"min-h-0.*?\n", "", body, count=1, flags=re.S)
body = body.replace("global_image_name", "image_name").replace("global_tag", "tag")
body = body.replace("multi-service-mode-", "ms-mode-")
body = body.replace("btn-group w-full flex", "push-mode-group")
body = body.strip()
if body.endswith("</motion>"):
    body = body[:-7] + "</div>"
# trim extra closing divs from modal wrapper
while body.count("</div>") > body.count("<div"):
    body = body.rsplit("</motion>", 1)[0] if "</motion>" in body else body.rsplit("</div>", 1)[0]

script = r'''<script setup>
import { inject, watch } from "vue";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { usePipelineMultiService } from "@/composables/usePipelineMultiService";

const props = defineProps({
  embedded: { type: Boolean, default: false },
});

const detail = inject(PIPELINE_DETAIL_KEY, null);
const editor = inject("pipelineEditor", null);

const {
  multiServiceFormData,
  savingMultiServiceConfig,
  parsingDockerfileForMultiService,
  loadFromPipeline,
  addServiceToMultiConfig,
  removeServiceFromMultiConfig,
  updateServiceName,
  updateServiceImageName,
  updateServiceTag,
  updateServicePush,
  getSingleServicePush,
  updateSingleServicePush,
  updateServiceEnabled,
  enableAllServices,
  disableAllServices,
  getMultiServiceDefaultImageName,
  parseDockerfileForMultiService,
  saveMultiServiceConfig,
} = usePipelineMultiService({
  formData: editor?.formData,
  getPipeline: () => editor?.editingPipeline?.value || detail?.pipeline?.value,
  embedded: props.embedded,
  onSaved: () => detail?.refresh?.(),
});

watch(
  () => editor?.editingPipeline?.value || detail?.pipeline?.value,
  (p) => {
    if (p) loadFromPipeline(p);
  },
  { immediate: true }
);
</script>
'''

tpl = f"""<template>
  <div class="pipeline-multi-service-tab space-y-4">
{body}
    <motion v-if="!embedded" class="mt-4 flex justify-end gap-2 border-t border-slate-200 pt-4">
      <Button type="button" size="sm" :disabled="savingMultiServiceConfig" @click="saveMultiServiceConfig">
        <span v-if="savingMultiServiceConfig" class="fas fa-spinner fa-spin mr-1"></span>
        <i v-else class="fas fa-save mr-1"></i>
        {{{{ savingMultiServiceConfig ? '保存中...' : '保存' }}}}
      </Button>
    </motion>
  </div>
</template>

{script}
"""
tpl = tpl.replace("<motion ", "<div ").replace("</motion>", "</div>")
out_path.write_text(tpl, encoding="utf-8")
print("ok", out_path.stat().st_size)
