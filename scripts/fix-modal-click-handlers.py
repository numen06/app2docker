#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"


def patch_pipeline():
    p = ROOT / "PipelinePanel.vue"
    t = p.read_text(encoding="utf-8")
    pairs = [
        ("showModal", "closeModal()"),
        ("showWebhookModal", "showWebhookModal = false"),
        ("showManualRunModal", "showManualRunModal = false"),
        ("showLogModal", "showLogModal = false"),
        ("showHistoryModal", "showHistoryModal = false"),
        ("showResourcePackageModal", "showResourcePackageModal = false"),
        ("showMultiServiceConfigModal", "showMultiServiceConfigModal = false"),
        ("showBuildConfigJsonModal", "showBuildConfigJsonModal = false"),
        ("showJsonCreateModal", "showJsonCreateModal = false"),
    ]
    for name, handler in pairs:
        old = (
            f'v-if="{name}"\n'
            '      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"\n'
            "     @click.self>"
        )
        new = (
            f'v-if="{name}"\n'
            '      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"\n'
            f'      @click.self="{handler}"'
        )
        t = t.replace(old, new)
    t = t.replace(
        'class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">',
        'class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>',
    )
    t = t.replace('class="my-8 w-full max-w-', 'class="relative z-10 mx-auto w-full max-w-')
    p.write_text(t, encoding="utf-8")


def patch_datasource():
    p = ROOT / "DataSourcePanel.vue"
    t = p.read_text(encoding="utf-8")
    rules = [
        ('v-if="showModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
         'v-if="showModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="closeModal"'),
        ('v-if="showDockerfileModal && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
         'v-if="showDockerfileModal && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="closeDockerfileModal"'),
        ('v-if="showDockerfileEditor && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
         'v-if="showDockerfileEditor && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="closeDockerfileEditor"'),
        ('v-if="showCommitModal && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
         'v-if="showCommitModal && currentSource" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="closeCommitModal"'),
    ]
    for a, b in rules:
        t = t.replace(a, b)
    t = t.replace('class="my-8 w-full max-w-', 'class="relative z-10 mx-auto w-full max-w-')
    t = t.replace(
        'class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">',
        'class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>',
    )
    p.write_text(t, encoding="utf-8")


def patch_build_config():
    p = ROOT / "BuildConfigEditor.vue"
    t = p.read_text(encoding="utf-8")
    t = t.replace("@click.self>", '@click.self="showJsonModal = false">')
    p.write_text(t, encoding="utf-8")


def patch_step_build():
    p = ROOT / "StepBuildPanel.vue"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        'v-if="showBuildConfigJsonModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
        'v-if="showBuildConfigJsonModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="showBuildConfigJsonModal = false"',
    )
    t = t.replace(
        'v-if="showUploadProgressModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self>',
        'v-if="showUploadProgressModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"',
    )
    p.write_text(t, encoding="utf-8")


def patch_agent_host():
    p = ROOT / "AgentHostManager.vue"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4" style="background-color: rgba(0,0,0,0.5);"',
        'class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"',
    )
    t = t.replace(
        'class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">',
        'class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>',
    )
    p.write_text(t, encoding="utf-8")


def main():
    patch_pipeline()
    patch_datasource()
    patch_build_config()
    patch_step_build()
    patch_agent_host()
    print("done")


if __name__ == "__main__":
    main()
