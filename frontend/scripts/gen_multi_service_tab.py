from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
body = (ROOT / "src/components/pipeline/detail/_multi_service_body.txt").read_text(
    encoding="utf-8"
)
body = body.replace("multi-service-mode-single", "ms-mode-single").replace(
    "multi-service-mode-multi", "ms-mode-multi"
)
footer = """
    <motion class="mt-4 flex justify-end gap-2 border-t border-slate-200 pt-4">
      <Button type="button" size="sm" :disabled="savingMultiServiceConfig" @click="saveMultiServiceConfig">
        <span v-if="savingMultiServiceConfig" class="fas fa-spinner fa-spin mr-1"></span>
        <i v-else class="fas fa-save mr-1"></i>
        {{ savingMultiServiceConfig ? '保存中...' : '保存' }}
      </Button>
    </motion>"""
footer = footer.replace("<motion", "<motion").replace("</motion>", "</motion>")
footer = footer.replace("motion", "div") if "motion" == "motion" else footer
footer = footer.replace("<motion", "<div").replace("</motion>", "</div>")

script_content = """<script setup>
import { inject, watch } from "vue";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { usePipelineMultiService } from "@/composables/usePipelineMultiService";

const detail = inject(PIPELINE_DETAIL_KEY);
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
} = usePipelineMultiService({ onSaved: () => detail.refresh() });

watch(
  () => detail.pipeline.value,
  (p) => {
    if (p) loadFromPipeline(p);
  },
  { immediate: true }
);
</script>"""

vue = f"""<template>
  <div class="pipeline-multi-service-tab">
{body}
{footer}
  </div>
</template>

{script_content}
"""
out = ROOT / "src/components/pipeline/detail/PipelineMultiServiceTab.vue"
out.write_text(vue, encoding="utf-8")
print("wrote", out)
