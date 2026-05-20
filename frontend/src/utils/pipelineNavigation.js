/** 流水线列表页导航（与侧栏「流水线」、AdminLayout tab=pipeline 一致） */

export const PIPELINE_LIST_LOCATION = {
  name: "admin",
  params: { tab: "pipeline" },
};

export function goToPipelineList(router) {
  return router.replace(PIPELINE_LIST_LOCATION);
}
