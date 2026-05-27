import axios from "axios";
import { ref } from "vue";

export function usePipelineDetail() {
  const pipeline = ref(null);
  const loading = ref(false);
  const error = ref(null);

  async function load(pipelineId, { silent = false } = {}) {
    if (!pipelineId) {
      pipeline.value = null;
      return false;
    }
    if (!silent) loading.value = true;
    error.value = null;
    try {
      const res = await axios.get(`/api/pipelines/${pipelineId}`);
      pipeline.value = res.data;
      return true;
    } catch (e) {
      console.error("加载流水线失败:", e);
      error.value =
        e.response?.data?.detail || e.message ||"加载流水线失败";
      pipeline.value = null;
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function refresh(pipelineId) {
    return load(pipelineId, { silent: true });
  }

  return {
    pipeline,
    loading,
    error,
    load,
    refresh,
  };
}
