<template>
  <header class="app-header">
    <!-- 左侧 Logo -->
    <router-link to="/" class="logo">📝 AI 论文写作系统</router-link>

    <!-- 中间导航 -->
    <nav class="nav-links">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-link"
        :class="{ active: isActive(item.path) }"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <!-- 右侧用户区 -->
    <div class="user-area">
      <template v-if="userStore.isLoggedIn">
        <el-dropdown @command="handleCommand">
          <span class="user-name">👤 {{ userStore.username || '用户' }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button size="small" class="login-btn" @click="router.push('/login')">登录</el-button>
      </template>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const navItems = [
  { path: '/', label: '首页' },
  { path: '/papers', label: '我的论文' },
  { path: '/references', label: '文献管理' }
]

/** 判断导航是否激活 */
function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

/** 下拉菜单命令处理 */
async function handleCommand(command: string) {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch (e) {
      return
    }
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
.app-header {
  height: 60px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  background: var(--primary-gradient);
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.25);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 28px;
  margin-left: 48px;
  flex: 1;
}

.nav-link {
  color: rgba(255, 255, 255, 0.72);
  font-size: 15px;
  transition: color 0.2s ease;

  &:hover {
    color: #fff;
  }

  &.active {
    color: #fff;
    font-weight: 700;
  }
}

.user-area {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.user-name {
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.login-btn {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.5);
  color: #fff;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: #fff;
    color: #fff;
  }
}
</style>