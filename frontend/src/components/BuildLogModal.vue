<template>
  <BaseDialog :model-value="modelValue" @update:model-value="onDialogClose">
    <div
      class="relative z-10 mx-auto flex max-h-[90vh] w-full max-w-[min(calc(100vw-1.5rem),1400px)] shrink-0 flex-col overflow-hidden rounded-lg shadow-xl"
      @click.stop
    >
      <div class="flex shrink-0 items-center justify-between border-b border-slate-700 bg-slate-900 px-4 py-3 text-white">
        <h3 class="flex items-center gap-2 text-lg font-semibold">
          <i class="fas fa-terminal"></i> 构建日志
        </h3>
        <button
          type="button"
          class="rounded-md p-2 text-slate-300 hover:bg-slate-800"
          aria-label="关闭"
          @click="close"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="flex flex-col overflow-hidden" style="height: 600px">
        <div class="log-toolbar">
          <Input v-model="searchTerm" type="text" placeholder="搜索..." class="h-8 min-w-[150px] bg-slate-700 text-slate-100" />
          <NativeSelect v-model="levelFilter" class="h-8 w-auto bg-slate-700 text-slate-100">
            <option value="all">全部</option>
            <option value="error">错误</option>
            <option value="warning">警告</option>
            <option value="success">成功</option>
            <option value="info">信息</option>
          </NativeSelect>
          <div class="flex gap-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              :class="autoScroll ? 'bg-slate-600' : ''"
              class="border-slate-600 text-slate-200"
              @click="autoScroll = !autoScroll"
              title="自动滚动"
            >
              <i class="fas fa-arrow-down"></i>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              :class="showLineNumber ? 'bg-slate-600' : ''"
              class="border-slate-600 text-slate-200"
              @click="showLineNumber = !showLineNumber"
              title="行号"
            >
              <i class="fas fa-list-ol"></i>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              :class="showTimestamp ? 'bg-slate-600' : ''"
              class="border-slate-600 text-slate-200"
              @click="showTimestamp = !showTimestamp"
              title="时间戳"
            >
              <i class="fas fa-clock"></i>
            </Button>
          </div>
          <div class="flex gap-1">
            <Button type="button" variant="outline" size="sm" class="border-slate-600 text-slate-200" @click="copyLog" title="复制">
              <i class="fas fa-copy"></i>
            </Button>
            <Button type="button" variant="outline" size="sm" class="border-slate-600 text-slate-200" @click="downloadLog" title="下载">
              <i class="fas fa-download"></i>
            </Button>
            <Button type="button" variant="outline" size="sm" class="border-slate-600 text-slate-200" @click="clearLog" title="清空">
              <i class="fas fa-trash"></i>
            </Button>
            <Button type="button" variant="outline" size="sm" class="border-slate-600 text-slate-200" @click="scrollToTop" title="滚动到顶部">
              <i class="fas fa-arrow-up"></i>
            </Button>
            <Button type="button" variant="outline" size="sm" class="border-slate-600 text-slate-200" @click="scrollToBottom" title="滚动到底部">
              <i class="fas fa-arrow-down"></i>
            </Button>
          </div>
          <div class="log-stats">{{ logs.length }} 行 | {{ filteredLogs.length }} 显示</div>
        </div>
        <div ref="logContainer" class="log-container">
          <div
            v-for="(log, index) in filteredLogs"
            :key="index"
            class="log-line"
            :class="log.level"
          >
            <span v-if="showLineNumber" class="log-line-number">{{ log.number }}</span>
            <span v-if="showTimestamp" class="log-timestamp">[{{ log.timestamp }}]</span>
            <span class="log-content" v-html="highlightSearch(log.text)"></span>
          </div>
        </div>
      </div>
    </div>
  </BaseDialog>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { copyToClipboard } from "../utils/clipboard.js";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const props = defineProps({ modelValue: Boolean });
const emit = defineEmits(["update:modelValue"]);

const logs = ref([]);
const searchTerm = ref("");
const levelFilter = ref("all");
const autoScroll = ref(true);
const showLineNumber = ref(true);
const showTimestamp = ref(true);
const logContainer = ref(null);

const filteredLogs = computed(() =>
  logs.value.filter((log) => {
    if (levelFilter.value !== "all" && log.level !== levelFilter.value) return false;
    if (searchTerm.value && !log.text.toLowerCase().includes(searchTerm.value.toLowerCase())) return false;
    return true;
  })
);

function addLog(text, level = "info") {
  const timestamp = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  if (!level || level === "info") {
    if (text.includes("❌") || text.includes("错误") || text.includes("失败") || text.includes("ERROR")) level = "error";
    else if (text.includes("✅") || text.includes("成功") || text.includes("完成") || text.includes("SUCCESS")) level = "success";
    else if (text.includes("⚠️") || text.includes("警告") || text.includes("WARNING")) level = "warning";
  }
  logs.value.push({ number: logs.value.length + 1, timestamp, text, level });
  if (autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight;
    });
  }
}

function highlightSearch(text) {
  if (!searchTerm.value) return text;
  const regex = new RegExp(`(${searchTerm.value})`, "gi");
  return text.replace(regex, "<mark>$1</mark>");
}

async function clearLog() {
  if (await showConfirm({ message: "确定要清空所有日志吗？", danger: true })) logs.value = [];
}

async function copyLog() {
  const text = logs.value.map((log) => log.text.trim()).filter((line) => line.length > 0).join("\n");
  const success = await copyToClipboard(text);
  success
    ? toastSuccess(`日志已复制到剪贴板 (${logs.value.length} 行)`)
    : toastError("复制失败，请手动选择文本复制");
}

function downloadLog() {
  const text = logs.value
    .map((log) => {
      let line = "";
      if (showLineNumber.value) line += `${log.number.toString().padStart(4, " ")} `;
      if (showTimestamp.value) line += `[${log.timestamp}] `;
      line += log.text.trim();
      return line;
    })
    .filter((line) => line.trim().length > 0)
    .join("\n");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `app2docker-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.log`;
  a.click();
  URL.revokeObjectURL(url);
}

function scrollToTop() {
  if (logContainer.value) {
    autoScroll.value = false;
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = 0;
    });
  }
}

function scrollToBottom() {
  if (logContainer.value) {
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight;
    });
  }
}

function onDialogClose(v) {
  if (!v) close();
  else emit("update:modelValue", v);
}

function close() {
  unlockBodyScroll();
  emit("update:modelValue", false);
}

function lockBodyScroll() {
  document.body.style.overflow = "hidden";
}
function unlockBodyScroll() {
  document.body.style.overflow = "";
}

const handleShowBuildLog = () => emit("update:modelValue", true);
const handleAddLog = (e) => addLog(e.detail.text, e.detail.level);

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) lockBodyScroll();
    else unlockBodyScroll();
  }
);

onMounted(() => {
  window.addEventListener("show-build-log", handleShowBuildLog);
  window.addEventListener("add-log", handleAddLog);
  if (props.modelValue) lockBodyScroll();
});

onUnmounted(() => {
  window.removeEventListener("show-build-log", handleShowBuildLog);
  window.removeEventListener("add-log", handleAddLog);
  unlockBodyScroll();
});

defineExpose({ addLog, clearLog });
</script>

<style scoped>
.log-toolbar {
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  padding: 6px 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.log-stats {
  color: #858585;
  font-size: 10px;
  margin-left: auto;
}
.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: var(--font-mono);
  height: calc(100% - 42px);
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
}
.log-line {
  padding: 4px 12px 4px 60px;
  border-left: 3px solid transparent;
  position: relative;
}
.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}
.log-line-number {
  position: absolute;
  left: 8px;
  top: 4px;
  color: #858585;
  font-size: 11px;
  width: 40px;
  text-align: right;
}
.log-timestamp {
  color: #858585;
  font-size: 11px;
  margin-right: 8px;
}
.log-line.error {
  border-left-color: #f48771;
  background: rgba(244, 135, 113, 0.05);
}
.log-line.error .log-content {
  color: #f48771;
}
.log-line.success {
  border-left-color: #89d185;
  background: rgba(137, 209, 133, 0.05);
}
.log-line.success .log-content {
  color: #89d185;
}
.log-line.warning {
  border-left-color: #e5c07b;
  background: rgba(229, 192, 123, 0.05);
}
.log-line.warning .log-content {
  color: #e5c07b;
}
.log-line.info {
  border-left-color: #61afef;
}
.log-line.info .log-content {
  color: #61afef;
}
</style>
