<template>
  <div v-if="paper" class="paper-detail">
    <div class="detail-header app-card app-card--lg">
      <div class="header-left">
        <h2 class="title">{{ paper.title }}</h2>
        <div class="meta">
          <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
          <span class="meta-item">📝 {{ wordCount }} 字</span>
          <span class="meta-item">📚 文献 {{ referenceCount }} 篇</span>
          <span class="meta-item">📅 {{ formatDate(paper.updated_at || paper.created_at) }}</span>
        </div>
      </div>
      <el-button type="primary" @click="exportMarkdown">📥 导出 Markdown</el-button>
    </div>

    <div class="detail-body">
      <div class="outline-panel app-card app-card--lg">
        <div class="panel-title">🗂️ 论文大纲</div>
        <div v-if="outlineSections.length" class="outline-list">
          <div v-for="(section, index) in outlineSections" :key="index" class="outline-item">
            <div class="section-title">
              <span class="section-index">{{ index + 1 }}</span>
              {{ section.title }}
              <span class="section-words">约 {{ section.word_count || 0 }} 字</span>
            </div>
            <ul v-if="section.points && section.points.length" class="section-points">
              <li v-for="(point, i) in section.points" :key="i">• {{ point }}</li>
            </ul>
          </div>
        </div>
        <div v-else class="empty-tip">暂无大纲内容</div>
      </div>

      <div class="content-panel app-card app-card--lg">
        <div class="panel-title">📄 论文全文预览</div>
        <div v-if="paper.content" class="markdown-body content-body" v-html="html"></div>
        <div v-else class="empty-tip">暂无正文内容，去工作台生成吧</div>
      </div>
    </div>
  </div>

  <div v-else class="empty-tip">请选择一篇论文查看详情</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import type { Paper, Outline, OutlineSection } from '@/api/paper'

const props = defineProps<{
  paper: Paper | null
}>()

interface DetailPaper extends Paper {
  references?: { id: number }[]
}

/** 解析大纲（容错处理，解析失败返回空数组） */
const outlineSections = computed<OutlineSection[]>(() => {
  const raw = props.paper?.outline
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as Outline | OutlineSection[]
    if (Array.isArray(parsed)) return parsed
    return parsed?.sections || []
  } catch (e) {
    return []
  }
})

/** 渲染 Markdown 全文 */
const html = computed(() => {
  try {
    return marked.parse(props.paper?.content || '') as string
  } catch (e) {
    return ''
  }
})

/** 正文字数 */
const wordCount = computed(() => (props.paper?.content || '').replace(/\s/g, '').length)

/** 文献数量 */
const referenceCount = computed(() => (props.paper as DetailPaper)?.references?.length || 0)

/** 状态标签类型 */
const statusType = computed<'info' | 'warning' | 'primary' | 'success'>(() => {
  const map: Record<string, 'info' | 'warning' | 'primary' | 'success'> = {
    draft: 'info',
    outline: 'warning',
    writing: 'primary',
    review: 'warning',
    completed: 'success'
  }
  return map[props.paper?.status || 'draft'] || 'info'
})

/** 状态文案 */
const statusLabel = computed(() => {
  const map: Record<string, string> = {
    draft: '草稿',
    outline: '大纲阶段',
    writing: '撰写中',
    review: '审核中',
    completed: '已完成'
  }
  return map[props.paper?.status || 'draft'] || props.paper?.status || ''
})

function formatDate(value: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

/** 前端导出 Markdown 文件 */
function exportMarkdown() {
  if (!props.paper) return
  const blob = new Blob([props.paper.content || '# ' + props.paper.title], {
    type: 'text/markdown;charset=utf-8'
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.paper.title}.md`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已开始下载 Markdown 文件')
}
</script>

<style scoped lang="scss">
.paper-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-header {
  padding: 20px 22px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  flex: 1;
  min-width: 260px;
}

.title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 10px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--text-secondary);
}

.detail-body {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 18px;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
}

.outline-panel,
.content-panel {
  padding: 18px 20px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 640px;
  overflow-y: auto;
}

.outline-item {
  border-left: 3px solid rgba(102, 126, 234, 0.4);
  padding-left: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-index {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: var(--primary-color);
  color: #fff;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.section-words {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
}

.section-points {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-secondary);

  li {
    margin: 3px 0;
  }
}

.content-body {
  max-height: 640px;
  overflow-y: auto;
}

.empty-tip {
  color: var(--text-secondary);
  font-size: 14px;
  padding: 24px 0;
  text-align: center;
}
</style>