<template>
  <div>
    <div v-if="papers.length" class="paper-grid">
      <div v-for="paper in papers" :key="paper.id" class="paper-card app-card">
        <div class="card-head">
          <h3 class="paper-title text-ellipsis" :title="paper.title">{{ paper.title }}</h3>
          <el-tag :type="statusType(paper.status)" size="small" effect="light">
            {{ statusText(paper.status) }}
          </el-tag>
        </div>

        <div class="meta-list">
          <div class="meta-item">📅 {{ formatDate(paper.created_at) }}</div>
          <div class="meta-item text-ellipsis" :title="paper.topic">🏷️ {{ paper.topic || '未设置选题' }}</div>
        </div>

        <div class="card-actions">
          <el-button size="small" type="primary" plain @click="emit('edit', paper.id)">编辑</el-button>
          <el-button size="small" type="success" plain @click="emit('generate', paper.id)">生成</el-button>
          <el-popconfirm
            title="确定要删除该论文吗？"
            confirm-button-text="确定"
            cancel-button-text="取消"
            @confirm="emit('remove', paper.id)"
          >
            <template #reference>
              <el-button size="small" type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">📄 还没有论文，点击上方按钮创建</div>
  </div>
</template>

<script setup lang="ts">
import type { Paper, PaperStatus } from '@/api/paper'

defineProps<{
  papers: Paper[]
}>()

const emit = defineEmits<{
  (e: 'edit', id: number): void
  (e: 'generate', id: number): void
  (e: 'remove', id: number): void
}>()

/** 状态标签类型 */
function statusType(status: PaperStatus | string): 'info' | 'warning' | 'primary' | 'success' {
  const map: Record<string, 'info' | 'warning' | 'primary' | 'success'> = {
    draft: 'info',
    outline: 'warning',
    writing: 'primary',
    review: 'warning',
    completed: 'success'
  }
  return map[status] || 'info'
}

/** 状态文案 */
function statusText(status: PaperStatus | string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    outline: '大纲阶段',
    writing: '撰写中',
    review: '审核中',
    completed: '已完成'
  }
  return map[status] || status
}

/** 格式化日期 */
function formatDate(value: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.paper-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

.paper-card {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.paper-title {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
}

.meta-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item {
  font-size: 13px;
  color: var(--text-secondary);
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
  color: var(--text-secondary);
  background: var(--card-bg);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  font-size: 15px;
}
</style>