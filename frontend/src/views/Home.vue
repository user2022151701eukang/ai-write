<template>
  <div class="home">
    <!-- 欢迎横幅 -->
    <section class="hero">
      <h1 class="hero-title">📝 AI 智能论文写作系统</h1>
      <p class="hero-subtitle">基于多 Agent 协作 + RAG 检索增强，实现论文全流程自动化</p>
      <div class="hero-tags">
        <span class="hero-tag">🤖 多 Agent 协作</span>
        <span class="hero-tag">📚 RAG 文献检索</span>
        <span class="hero-tag">🔄 LangGraph 工作流</span>
        <span class="hero-tag">✨ 智能润色优化</span>
      </div>
      <el-button class="hero-btn" size="large" @click="router.push('/papers/create')">
        🚀 开始写作
      </el-button>
    </section>

    <!-- 大模型未配置提示 -->
    <el-alert
      v-if="llmNotConfigured"
      class="llm-alert"
      type="warning"
      :closable="false"
      show-icon
      title="尚未配置大模型 API Key，请在 backend/.env 中填写 QWEN_API_KEY 后重启后端"
    />

    <!-- 核心功能 -->
    <section class="section">
      <h2 class="section-title">核心功能</h2>
      <div class="feature-grid">
        <div v-for="item in features" :key="item.title" class="feature-card app-card">
          <div class="feature-icon">{{ item.icon }}</div>
          <div class="feature-title">{{ item.title }}</div>
          <div class="feature-desc">{{ item.desc }}</div>
        </div>
      </div>
    </section>

    <!-- 技术架构 -->
    <section class="section">
      <h2 class="section-title">技术架构</h2>
      <div class="tech-grid">
        <div v-for="item in techs" :key="item.name" class="tech-card app-card">
          <span class="tech-name">{{ item.name }}</span>
          <span class="tech-desc">{{ item.desc }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SERVER_BASE } from '@/api/request'

const router = useRouter()
const llmNotConfigured = ref(false)

const features = [
  { icon: '💡', title: '智能选题推荐', desc: '结合研究领域与关键词，自动推荐可行选题方向' },
  { icon: '🗂️', title: '大纲自动生成', desc: '按论文类型与字数要求，一键生成结构化大纲' },
  { icon: '✍️', title: '分章节撰写', desc: '多 Agent 协作逐章撰写，支持实时流式输出' },
  { icon: '📚', title: '文献检索引用', desc: '基于 RAG 的语义检索，自动生成标准引用格式' },
  { icon: '✨', title: '论文润色优化', desc: '语言、逻辑、格式多角度润色，提升学术表达' },
  { icon: '🕒', title: '版本管理', desc: '论文与章节自动保存，随时回溯查看历史内容' }
]

const techs = [
  { name: 'FastAPI', desc: '高性能异步后端框架，提供完整 REST 接口' },
  { name: 'LangChain', desc: '大模型应用编排，统一模型与检索调用' },
  { name: 'LangGraph', desc: '多 Agent 状态机工作流，掌控论文生成流程' },
  { name: 'ChromaDB', desc: '向量数据库，支撑文献语义检索与召回' },
  { name: 'Vue 3', desc: '组合式 API 前端框架，响应式交互体验' },
  { name: 'Element Plus', desc: '企业级 UI 组件库，快速构建专业界面' }
]

/** 检查后端健康状态，判断大模型是否已配置 */
onMounted(async () => {
  try {
    const res = await fetch(`${SERVER_BASE}/health`)
    if (!res.ok) return
    const data = await res.json()
    if (data?.llm === 'not_configured') {
      llmNotConfigured.value = true
    }
  } catch (e) {
    // 后端未启动时静默忽略
  }
})
</script>

<style scoped lang="scss">
.home {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.hero {
  background: var(--primary-gradient);
  border-radius: 16px;
  padding: 56px 40px;
  text-align: center;
  color: #fff;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.25);
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 12px;
}

.hero-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 22px;
}

.hero-tags {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}

.hero-tag {
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.hero-btn {
  background: #fff;
  color: var(--primary-color);
  border: none;
  font-weight: 600;
  padding: 22px 40px;

  &:hover {
    background: #f4f5ff;
    color: var(--primary-color);
  }
}

.llm-alert {
  border-radius: 12px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

.feature-card {
  padding: 20px;
}

.feature-icon {
  font-size: 26px;
  margin-bottom: 10px;
}

.feature-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
}

.feature-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.tech-card {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tech-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--primary-color);
}

.tech-desc {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>