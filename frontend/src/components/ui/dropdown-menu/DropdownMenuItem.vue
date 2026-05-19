<template>
  <RadixDropdownMenuItem
    class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-slate-100 focus:bg-slate-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
    v-bind="$attrs"
  >
    <slot />
  </RadixDropdownMenuItem>
</template>

<script setup>
import { DropdownMenuItem as RadixDropdownMenuItem } from 'radix-vue'
</script>
