<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <!-- 路由出口：Login.vue 或 HomeView.vue 会渲染在这里 -->
  <RouterView />
</template>

<style>
/* 简单的全局重置，保证占满全屏 */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}
</style>
