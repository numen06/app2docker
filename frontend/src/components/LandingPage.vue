<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
    <header class="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <RouterLink to="/" class="flex items-center gap-2 font-semibold text-slate-900">
          <AppIcon  name="box-open" class="text-blue-600" />
          <span>App2Docker</span>
        </RouterLink>
        <div class="flex shrink-0 items-center gap-2">
          <Button variant="ghost" size="sm" class="min-h-11 px-2 sm:px-3" @click="$router.push('/login')">
            登录
          </Button>
          <Button size="sm" class="min-h-11" @click="$router.push('/register')">注册</Button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 sm:px-6">
      <section class="grid gap-10 py-10 sm:gap-12 sm:py-14 lg:grid-cols-2 lg:items-center lg:gap-14">
        <div class="space-y-5 sm:space-y-6">
          <p class="text-sm font-medium uppercase tracking-wide text-blue-600">
            Docker 镜像构建平台
          </p>
          <h1 class="text-balance text-3xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            把应用一键打成镜像，交付更简单
          </h1>
          <p class="max-w-xl text-pretty text-base text-slate-600 sm:text-lg">
            从代码到镜像、从构建到部署，App2Docker 为团队提供统一的镜像交付工作台。支持流水线编排与复制、模板复用、跨仓库镜像迁移、多环境导出与主机联动部署。
          </p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in heroTags"
              :key="tag"
              class="rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700"
            >
              {{ tag }}
            </span>
          </div>
          <p class="text-sm text-slate-500">
            注册后即可创建团队，邀请成员协作；已有账号请使用右上角登录。
          </p>
        </div>

        <div class="w-full">
          <ProductMockup variant="dashboard" label="管理后台 · 仪表盘" />
        </div>
      </section>

      <section class="border-t border-slate-200/80 py-12 sm:py-16">
        <div class="mb-10 text-center sm:mb-12">
          <h2 class="text-2xl font-bold text-slate-900 sm:text-3xl">覆盖镜像交付全流程</h2>
          <p class="mx-auto mt-3 max-w-2xl text-pretty text-slate-600">
            构建、协作、部署在同一平台完成，减少工具切换与手工操作。
          </p>
        </div>

        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <article
            v-for="feature in features"
            :key="feature.title"
            class="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
          >
            <div class="border-b border-slate-100 p-4 sm:p-5">
              <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                <AppIcon :name="feature.icon" class="text-blue-600" />
              </div>
              <h3 class="font-semibold text-slate-900">{{ feature.title }}</h3>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">{{ feature.desc }}</p>
            </div>
            <div class="mt-auto bg-slate-50/80 p-3 sm:p-4">
              <ProductMockup :variant="feature.mockup" :label="feature.mockupLabel" compact />
            </div>
          </article>
        </div>
      </section>

      <section class="border-t border-slate-200/80 py-12 sm:py-16">
        <div class="mb-8 sm:mb-10">
          <h2 class="text-2xl font-bold text-slate-900 sm:text-3xl">为什么选择 App2Docker</h2>
          <p class="mt-3 max-w-2xl text-slate-600">
            面向研发与运维团队，把常见镜像交付场景做成可配置、可复用、可审计的标准流程。
          </p>
        </div>

        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div
            v-for="item in advantages"
            :key="item.title"
            class="flex gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
          >
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-50">
              <AppIcon :name="item.icon" class="text-sm text-blue-600" />
            </div>
            <div>
              <div class="font-medium text-slate-900">{{ item.title }}</div>
              <p class="mt-1 text-sm text-slate-600">{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </section>
    </main>

    <footer class="border-t border-slate-200 bg-white">
      <div class="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <div class="flex items-center gap-2 font-semibold text-slate-900">
              <AppIcon  name="box-open" class="text-blue-600" />
              <span>App2Docker</span>
            </div>
            <p class="mt-3 text-sm leading-relaxed text-slate-600">
              团队级 Docker 镜像构建与交付平台，让构建、导出与部署流程更清晰、更可协作。
            </p>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-slate-900">产品能力</h3>
            <ul class="mt-3 space-y-2 text-sm text-slate-600">
              <li>流水线、复制与多阶段构建</li>
              <li>模板与数据源管理</li>
              <li>镜像导出、仓库推送与跨仓迁移</li>
              <li>主机部署与任务追踪</li>
            </ul>
          </div>
          <div class="sm:col-span-2 lg:col-span-1">
            <h3 class="text-sm font-semibold text-slate-900">快速开始</h3>
            <p class="mt-3 text-sm text-slate-600">
              点击右上角注册创建账号，登录后即可进入管理后台配置流水线与团队。
            </p>
          </div>
        </div>
        <p class="mt-10 border-t border-slate-100 pt-6 text-center text-sm text-slate-500">
          © {{ year }} App2Docker · Docker 镜像构建平台
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
import Button from "@/components/ui/button/Button.vue";
import ProductMockup from "@/components/landing/ProductMockup.vue";

const year = new Date().getFullYear();

const heroTags = ["流水线构建","镜像迁移","模板复用","团队权限","主机部署"];

const features = [
  {
    icon:"gears",
    title:"流水线与构建",
    desc:"多阶段 Dockerfile、Webhook/Cron 触发；支持复制流水线快速复用配置，构建日志实时查看。",
    mockup:"pipeline",
    mockupLabel:"流水线 · 构建任务",
  },
  {
    icon:"right-left",
    title:"镜像迁移",
    desc:"在源/目标仓库间同步镜像，支持路径、标签与定时任务，适合多环境、多区域仓库对齐。",
    mockup:"pipeline",
    mockupLabel:"镜像迁移 · 任务列表",
  },
  {
    icon:"users",
    title:"团队协作",
    desc:"团队、成员与邀请链接统一管理，角色与菜单权限可控，多人共用模板与流水线。",
    mockup:"team",
    mockupLabel:"团队 · 成员管理",
  },
  {
    icon:"rocket",
    title:"部署联动",
    desc:"关联 Agent/SSH/Portainer 主机与部署任务，从镜像构建到环境上线形成闭环。",
    mockup:"deploy",
    mockupLabel:"部署 · 任务列表",
  },
];

const advantages = [
  {
    icon:"layer-group",
    title:"多阶段构建",
    desc:"支持复杂应用的镜像分层与构建阶段编排。",
  },
  {
    icon:"file-code",
    title:"模板管理",
    desc:"Dockerfile 与构建模板可复用、可版本化。",
  },
  {
    icon:"cloud-arrow-up",
    title:"导出与迁移",
    desc:"镜像 tar 导出、仓库推送，或跨仓库定时/手动迁移同步。",
  },
  {
    icon:"shield-halved",
    title:"权限控制",
    desc:"团队级隔离，成员角色与资源访问可控。",
  },
];
</script>
