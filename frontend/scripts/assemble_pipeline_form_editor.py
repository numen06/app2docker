from pathlib import Path

root = Path(__file__).resolve().parents[1]
form = (root / "src/components/pipeline/_form_inner.html").read_text(encoding="utf-8")
form = form.replace('@submit.prevent="savePipeline"', "@submit.prevent")

panel = (root / "src/components/PipelinePanel.vue").read_text(encoding="utf-8")
lines = panel.splitlines()
res_modal = "\n".join(lines[2910:3007])
build_modal = "\n".join(lines[3496:3562])

keys = """
formData activeTab editingPipeline gitSources templates registries projectTypesList
branchesAndTags refreshingBranches availableDockerfiles scanningDockerfiles dockerfilesError
repoVerified services loadingServices servicesError filteredTemplates buildConfigJson
buildConfigJsonText buildConfigJsonError dockerfileContentText loadingDockerfile
jsonEditorExtensions dockerfileEditorExtensions resourcePackages showResourcePackageModal
showBuildConfigJsonModal isAllBranchesSelected deployTaskList
onSourceSelected refreshBranches scanDockerfiles onBranchChanged copyBuildConfigJson
resetBuildConfigJson applyBuildConfigJson loadDockerfileFromRepo applyDockerfileContent
loadServices onPushModeChange toggleService onServiceSelectionChange selectAllServices
deselectAllServices removeService getServiceConfig getServiceDefaultImageName
onServiceImageNameBlur resetServiceImageName toggleResourcePackage isResourcePackageSelected
getResourcePackageName removeResourcePackage getResourcePackageConfig updateResourcePackagePath
onDockerfileSourceChange onTemplateChange formatGitUrl regenerateWebhookToken
regenerateWebhookSecret addBranchTagMapping addPostBuildWebhook removePostBuildWebhook
removeBranchTagMapping toggleAllBranches onPostBuildWebhookBranchesInput onDeployTaskSelected
closeBuildConfigJsonModal saveBuildConfigJson
""".split()

script_lines = [
    'import { inject } from "vue";',
    'import Button from "@/components/ui/button/Button.vue";',
    'import { Codemirror } from "vue-codemirror";',
    "",
    'const editor = inject("pipelineEditor");',
]
for k in keys:
    script_lines.append(f"const {k} = editor.{k};")

out = f"""<template>
  <div class="pipeline-form-editor">
{form}
{res_modal}
{build_modal}
  </motion.div>
</template>

<script setup>
{chr(10).join(script_lines)}
</script>
"""
out = out.replace("</motion.div>", "</div>").replace('<motion.div class="pipeline-form-editor">', '<div class="pipeline-form-editor">')

dest = root / "src/components/pipeline/PipelineFormEditor.vue"
dest.write_text(out, encoding="utf-8")
print("wrote", dest, "size", dest.stat().st_size)
