<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
    <header class="border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <RouterLink to="/" class="flex items-center gap-2 font-semibold text-slate-900">
          <i class="fas fa-box-open text-blue-600"></i>
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

    <main class="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <section class="grid gap-8 sm:gap-10 lg:grid-cols-[1.15fr_1fr] lg:items-center">
        <div class="space-y-5 sm:space-y-6">
          <p class="text-sm font-medium uppercase tracking-wide text-blue-600">
            Docker 镜像构建平台
          </p>
          <h1 class="text-balance text-3xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            把应用一键打成镜像，交付更简单
          </h1>
          <p class="max-w-xl text-pretty text-base text-slate-600 sm:text-lg">
            流水线构建、模板与数据源管理、主机与部署一站式协作；面向团队的镜像交付工作台。
          </p>
          <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Button size="lg" class="w-full sm:w-auto" @click="$router.push('/register')">
              <i class="fas fa-user-plus"></i>
              立即注册
            </Button>
            <Button variant="outline" size="lg" class="w-full sm:w-auto" @click="$router.push('/login')">
              <i class="fas fa-sign-in-alt"></i>
              已有账号登录
            </Button>
          </div>
        </div>

        <Card class="shadow-md shadow-slate-200/60">
          <CardHeader>
            <CardTitle>核心能力</CardTitle>
            <CardDescription>覆盖构建、导出、流水线与部署的常见路径。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div
              v-for="item in highlights"
              :key="item.title"
              class="flex gap-3 rounded-lg border border-slate-100 bg-slate-50/80 p-3 sm:p-4"
            >
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white shadow-sm">
                <i :class="['fas', item.icon, 'text-blue-600']"></i>
              </div>
              <div>
                <div class="font-medium text-slate-900">{{ item.title }}</div>
                <p class="mt-1 text-sm text-slate-600">{{ item.desc }}</p>
              </div>
            </div>
          </CardContent>
          <CardFooter class="flex-col gap-3 sm:flex-row sm:justify-between">
            <p class="text-sm text-slate-600">几分钟即可上手，登录后进入管理后台。</p>
            <Button @click="$router.push('/login')">进入控制台</Button>
          </CardFooter>
        </Card>
      </section>
    </main>

    <footer class="border-t border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
      <p class="break-words">© {{ year }} App2Docker · Docker 镜像构建平台</p>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardDescription from "@/components/ui/card/CardDescription.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import CardFooter from "@/components/ui/card/CardFooter.vue";

const year = new Date().getFullYear();

const highlights = [
  {
    icon: "fa-gears",
    title: "流水线与构建",
    desc: "多阶段构建、模板参数与导出一体化配置。",
  },
  {
    icon: "fa-users",
    title: "团队协作",
    desc: "成员与邀请管理，便于多人共用镜像交付流程。",
  },
  {
    icon: "fa-rocket",
    title: "部署联动",
    desc: "主机与部署任务视图，串联构建到上线。",
  },
];
</script>
