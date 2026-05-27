<template>
  <div
    v-if="totalPages > 1"
    class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
  >
    <p class="text-sm text-slate-500">
      显示第 {{ total > 0 ? (page - 1) * pageSize + 1 : 0 }} -
      {{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条
    </p>
    <nav class="flex flex-wrap items-center gap-1" aria-label="分页">
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        aria-label="第一页"
        @click="$emit('update:page', 1)"
      >
        <AppIcon name="angle-double-left" class="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        aria-label="上一页"
        @click="$emit('update:page', page - 1)"
      >
        <AppIcon name="angle-left" class="h-4 w-4" />
      </Button>
      <template v-for="p in visiblePages" :key="'p-' + p">
        <span v-if="p === '...'" class="px-2 text-sm text-slate-400">...</span>
        <Button
          v-else
          :variant="p === page ? 'default' : 'outline'"
          size="sm"
          class="min-w-9"
          @click="$emit('update:page', p)"
        >
          {{ p }}
        </Button>
      </template>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= totalPages"
        aria-label="下一页"
        @click="$emit('update:page', page + 1)"
      >
        <AppIcon name="angle-right" class="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= totalPages"
        aria-label="最后一页"
        @click="$emit('update:page', totalPages)"
      >
        <AppIcon name="angle-double-right" class="h-4 w-4" />
      </Button>
    </nav>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Button from "@/components/ui/button/Button.vue";

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, default: 10 },
  total: { type: Number, default: 0 },
  totalPages: { type: Number, default: 0 },
});

defineEmits(["update:page"]);

const visiblePages = computed(() => {
  const total = props.totalPages;
  const current = props.page;
  const pages = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i);
    pages.push("...");
    pages.push(total);
  } else if (current >= total - 3) {
    pages.push(1);
    pages.push("...");
    for (let i = total - 4; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    pages.push("...");
    for (let i = current - 1; i <= current + 1; i++) pages.push(i);
    pages.push("...");
    pages.push(total);
  }

  return pages.filter((p, i, arr) => p !=="..." || arr.indexOf(p) === i);
});
</script>
