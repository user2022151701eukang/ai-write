<template>
  <Header />
  <main class="app-main">
    <router-view />
  </main>
  <footer class="app-footer">© 2026 AI 论文写作系统 | 基于多 Agent 协作技术</footer>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Header from '@/components/common/Header.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 已登录时刷新页面后同步用户信息
onMounted(() => {
  if (userStore.isLoggedIn && !userStore.user) {
    userStore.fetchCurrentUser()
  }
})
</script>

<style scoped lang="scss">
.app-footer {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2c3e50;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
}
</style>