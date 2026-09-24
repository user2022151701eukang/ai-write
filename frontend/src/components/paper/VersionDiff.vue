<template>
  <div class="version-diff">
    <!-- 差异汇总 -->
    <div class="diff-summary">
      <el-tag type="success" effect="light">新增 {{ summary.added }}</el-tag>
      <el-tag type="danger" effect="light">删除 {{ summary.removed }}</el-tag>
      <el-tag type="warning" effect="light">修改 {{ summary.modified }}</el-tag>
      <el-tag type="info" effect="light">未变化 {{ summary.unchanged }}</el-tag>
    </div>

    <div v-if="!diff" class="empty-tip">暂无差异数据</div>
    <div v-else-if="allUnchanged" class="empty-tip">两个版本内容完全一致</div>

    <template v-else>
      <!-- 有变化的维度 -->
      <div v-for="dim in changedDimensions" :key="dim.key" class="dimension-block">
        <div class="dimension-header">
          <span class="dimension-label">{{ dim.label }}</span>
          <el-tag :type="statusTagType(dim.status)" size="small">{{ statusLabel(dim.status) }}</el-tag>
        </div>

        <!-- 行内差异：标题 / 摘要 / 关键词 -->
        <div v-if="dim.segments && dim.segments.length" class="inline-text">
          <span
            v-for="(seg, index) in dim.segments"
            :key="index"
            :class="segmentClass(seg.type)"
          >{{ seg.text }}</span>
        </div>

        <!-- 逐项差异：大纲 / 章节 / 文献 -->
        <div v-else-if="dim.items && dim.items.length" class="item-list">
          <div v-for="item in changedItems(dim)" :key="item.key" class="diff-item">
            <div class="item-header">
              <span class="item-title">{{ item.title }}</span>
              <el-tag :type="statusTagType(item.status)" size="small" effect="plain">
                {{ statusLabel(item.status) }}
              </el-tag>
              <span v-if="wordChange(item)" class="word-change">{{ wordChange(item) }}</span>
            </div>
            <div v-if="item.old_title" class="old-title">原名称：{{ item.old_title }}</div>
            <div v-if="item.segments && item.segments.length" class="segment-block">
              <span
                v-for="(seg, index) in item.segments"
                :key="index"
                :class="segmentClass(seg.type)"
              >{{ seg.text }}</span>
            </div>
            <div v-if="item.truncated" class="truncate-tip">差异内容过长，已截断显示</div>
          </div>

          <div v-if="unchangedItems(dim).length" class="unchanged-items">
            未变化：{{ unchangedItems(dim).map((i) => i.title).join('、') }}
          </div>
        </div>

        <div v-else class="empty-line">（无内容）</div>
      </div>

      <!-- 未变化的维度：折叠弱化显示 -->
      <el-collapse v-if="unchangedDimensions.length" class="unchanged-collapse">
        <el-collapse-item :title="`未变化：${unchangedLabels}`" name="unchanged">
          <div v-for="dim in unchangedDimensions" :key="dim.key" class="unchanged-dim">
            <span class="unchanged-label">{{ dim.label }}</span>
            <span class="unchanged-status">无变化</span>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiffDimension, DiffItem, DiffSegment, VersionDiff } from '@/api/version'

const props = defineProps<{
  diff?: VersionDiff | null
}>()

/** 差异汇总（无数据时默认全 0） */
const summary = computed(() => {
  return props.diff?.summary || { added: 0, removed: 0, modified: 0, unchanged: 0 }
})

/** 所有维度 */
const dimensions = computed<DiffDimension[]>(() => props.diff?.dimensions || [])

/** 有变化的维度 */
const changedDimensions = computed(() => dimensions.value.filter((d) => d.status !== 'unchanged'))

/** 未变化的维度 */
const unchangedDimensions = computed(() => dimensions.value.filter((d) => d.status === 'unchanged'))

/** 未变化维度的名称串 */
const unchangedLabels = computed(() => unchangedDimensions.value.map((d) => d.label).join('、'))

/** 是否两个版本完全一致 */
const allUnchanged = computed(() => dimensions.value.every((d) => d.status === 'unchanged'))

/** 维度内有变化的差异项 */
function changedItems(dim: DiffDimension): DiffItem[] {
  return (dim.items || []).filter((item) => item.status !== 'unchanged')
}

/** 维度内无变化的差异项 */
function unchangedItems(dim: DiffDimension): DiffItem[] {
  return (dim.items || []).filter((item) => item.status === 'unchanged')
}

/** 状态对应的标签颜色 */
function statusTagType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  const map: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
    added: 'success',
    removed: 'danger',
    modified: 'warning',
    unchanged: 'info'
  }
  return map[status] || 'info'
}

/** 状态文案 */
function statusLabel(status: string): string {
  const map: Record<string, string> = {
    added: '新增',
    removed: '删除',
    modified: '修改',
    unchanged: '无变化'
  }
  return map[status] || status
}

/** 差异片段的样式类 */
function segmentClass(type: DiffSegment['type']): string {
  return `seg seg-${type}`
}

/** 字数变化文案（仅 modified 且两端都有字数时展示） */
function wordChange(item: DiffItem): string {
  if (item.status !== 'modified') return ''
  if (item.word_count_old == null || item.word_count_new == null) return ''
  return `${item.word_count_old} → ${item.word_count_new} 字`
}
</script>

<style scoped lang="scss">
.version-diff {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diff-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-tip {
  color: var(--text-secondary);
  font-size: 14px;
  padding: 32px 0;
  text-align: center;
}

.dimension-block {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--card-bg);
  padding: 14px 16px;
}

.dimension-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;

  .dimension-label {
    font-size: 14px;
    font-weight: 700;
  }
}

/* 行内差异 */
.inline-text {
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 逐项差异 */
.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diff-item {
  border-left: 3px solid rgba(102, 126, 234, 0.35);
  padding-left: 12px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  .item-title {
    font-size: 13px;
    font-weight: 600;
  }

  .word-change {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.old-title {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.segment-block {
  margin-top: 6px;
  padding: 8px 10px;
  background: #fafbfc;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 差异片段公共样式 */
.seg {
  border-radius: 3px;
}

.seg-insert {
  background: #e7f7ee;
  color: #1f7a4d;
}

.seg-delete {
  background: #fdecec;
  color: #b23b3b;
  text-decoration: line-through;
}

.seg-equal {
  color: var(--text-primary);
}

.truncate-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #e6a23c;
}

.empty-line {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 未变化内容弱化 */
.unchanged-items {
  font-size: 12px;
  color: var(--text-secondary);
}

.unchanged-collapse {
  border: none;

  :deep(.el-collapse-item__header) {
    height: 40px;
    padding: 0 14px;
    font-size: 13px;
    color: var(--text-secondary);
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 10px;
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding: 10px 14px 0;
  }
}

.unchanged-dim {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 0;

  .unchanged-status {
    color: #9ca3af;
  }
}
</style>