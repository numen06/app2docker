#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"


def fix_mismatched_button_tags(text: str) -> str:
    # <button ...></Button> -> </button>
    text = re.sub(
        r"(<button\b[^>]*>)\s*</Button>",
        r"\1</button>",
        text,
        flags=re.IGNORECASE,
    )
    # <Button ...></button> -> </Button>
    text = re.sub(
        r"(<Button\b[^>]*>)\s*</button>",
        r"\1</Button>",
        text,
        flags=re.IGNORECASE,
    )
    return text


def fix_docker_manager():
    p = ROOT / "DockerManager.vue"
    t = p.read_text(encoding="utf-8")

    t = fix_mismatched_button_tags(t)

    # Tab buttons: native button with tailwind active state
    old_tabs = '''        <ul class="nav nav-tabs border-0">
          <li class="nav-item">
            <button
              class="rounded-md px-4 py-2 text-sm font-medium transition"
              :class="{ active: activeTab === 'containers' }"
              @click="activeTab = 'containers'"
              type="button"
            >
              <i class="fas fa-cubes"></i> 容器管理
              <Badge v-if="containerTotal > 0" variant="info" class="ml-1">{{
                containerTotal
              }}</Badge>
            </Button>
          </li>
          <li class="nav-item">
            <button
              class="rounded-md px-4 py-2 text-sm font-medium transition"
              :class="{ active: activeTab === 'images' }"
              @click="activeTab = 'images'"
              type="button"
            >
              <i class="fas fa-images"></i> 镜像管理
              <Badge v-if="imageTotal > 0" variant="default" class="ml-1">{{
                imageTotal
              }}</Badge>
            </Button>
          </li>
        </ul>'''

    new_tabs = '''        <ul class="nav nav-tabs mb-0 border-0" role="tablist">
          <li class="nav-item" role="presentation">
            <button
              type="button"
              class="nav-link"
              :class="{ active: activeTab === 'containers' }"
              @click="activeTab = 'containers'"
            >
              <i class="fas fa-cubes"></i> 容器管理
              <Badge v-if="containerTotal > 0" variant="info" class="ml-1">{{
                containerTotal
              }}</Badge>
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button
              type="button"
              class="nav-link"
              :class="{ active: activeTab === 'images' }"
              @click="activeTab = 'images'"
            >
              <i class="fas fa-images"></i> 镜像管理
              <Badge v-if="imageTotal > 0" variant="default" class="ml-1">{{
                imageTotal
              }}</Badge>
            </button>
          </li>
        </ul>'''

    if old_tabs in t:
        t = t.replace(old_tabs, new_tabs)

    # Header buttons on blue background
    t = t.replace(
        'variant="outline" size="sm"\n            @click="refreshDockerInfo(false)"',
        'variant="outline" size="sm" class="border-white/60 bg-white/10 text-white hover:bg-white/20"\n            @click="refreshDockerInfo(false)"',
    )
    t = t.replace(
        'variant="outline" size="sm"\n            @click="forceRefreshDockerInfo()"',
        'variant="outline" size="sm" class="border-white/60 bg-white/10 text-white hover:bg-white/20"\n            @click="forceRefreshDockerInfo()"',
    )

  t = t.replace('class="row g-2"', 'class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-2"')
    t = re.sub(r'\s*<div class="col-6 col-md-2"[^>]*>\s*', '\n          ', t)
    t = re.sub(r'\s*</motion.div>\s*(?=\n\s*<!--|\n\s*<motion.div class="col-|\n\s*<div class="info-item")', '\n', t)
    # Remove extra closing divs from col removal - careful

    p.write_text(t, encoding="utf-8")
    print("DockerManager.vue updated")


def fix_agent_host_manager():
    p = ROOT / "AgentHostManager.vue"
    t = p.read_text(encoding="utf-8")

    t = fix_mismatched_button_tags(t)

    t = t.replace(
        '<motion.div class="btn-group" role="group">',
        '<div class="flex flex-wrap gap-2" role="group">',
    )
    t = t.replace(
        '            </div>\n            <div class="btn-group filter-dropdown-group">',
        '            </div>\n            <div class="relative btn-group filter-dropdown-group">',
    )
    # Only first btn-group was filter - fix closing tag
    t = t.replace(
        '              </label>\n            </div>\n            <div class="relative btn-group filter-dropdown-group">',
        '              </label>\n            </div>\n            <motion.div class="relative btn-group filter-dropdown-group">',
    )

    # Fix the opening we changed - use div not motion
    t = t.replace('<motion.div class="flex flex-wrap gap-2"', '<div class="flex flex-wrap gap-2"')
    t = t.replace('class="btn-group btn-group-sm w-full"', 'class="flex w-full gap-1"')

    # Hide btn-check inputs properly
    if '.btn-check' not in t[t.find('<style scoped>'):]:
        pass

    p.write_text(t, encoding="utf-8")
    print("AgentHostManager.vue updated")


if __name__ == "__main__":
    fix_docker_manager()
    fix_agent_host_manager()
