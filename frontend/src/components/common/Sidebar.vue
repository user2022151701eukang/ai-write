<template>
  <aside class="chapter-sidebar">
    <div class="sidebar-header">
      <span class="title">📚 章节列表</span>
      <span class="count">{{ chapters.length }}</span>
    </div>

    <div class="chapter-list">
      <div
        v-for="(chapter, index) in chapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ active: chapter.id === activeId }"
        @click="emit('select', chapter)"
      >
        <span class="index">{{ index + 1 }}</span>
        <div class="info">
          <div class="chapter-title text-ellipsis" :title="chapter.title">{{ chapter.title }}</div>
          <div class="chapter-meta">{{ chapter.word_count || 0 }} 字</div>
        </div>
        <el-icon class="remove-icon" @click.stop="handleRemove(chapter.id)">
          <Delete />
        </el-icon>
      </div>

      <div v-if="!chapters.length" class="empty">暂无章节</div>
    </div>

    <div class="sidebar-footer">
      <el-button type="primary" class="add-btn" @click="emit('add')">+ 新增章节</el-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import type { Chapter } from '@/api/chapter'

const props = defineProps<{
  chapters: Chapter[]
  activeId?: number
}>()

const emit = defineEmits<{
  (e: 'select', chapter: Chapter): void
  (e: 'add'): void
  (e: 'remove', id: number): void
}>()

/** 删除章节（二次确认） */
async function handleRemove(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除该章节吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (e) {
    return
  }
  emit('remove', id)
}
</script>

<style scoped lang="scss">
.chapter-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);

  .title {
    font-weight: 600;
    font-size: 14px;
  }

  .count {
    font-size: 12px;
    color: var(--text-secondary);
    background: #f0f2f8;
    border-radius: 10px;
    padding: 1px 8px;
  }
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: #f5f6fb;

    .remove-icon {
      opacity: 1;
    }
  }

  &.active {
    background: rgba(102, 126, 234, 0.12);

    .index {
      background: var(--primary-color);
      color: #fff;
    }

    .chapter-title {
      color: var(--primary-color);
      font-weight: 600;
    }
  }
}

.index {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 6px;
  background: #f0f2f8;
  color: var(--text-secondary);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info {
  flex: 1;
  min-width: 0;
}

.chapter-title {
  font-size: 13px;
}

.chapter-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.remove-icon {
  opacity: 0;
  color: var(--text-secondary);
  transition: opacity 0.2s ease;

  &:hover {
    color: #f56c6c;
  }
}

.empty {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 24px 0;
}

.sidebar-footer {
  padding: 10px;
  border-top: 1px solid var(--border-color);

  .add-btn {
    width: 100%;
  }
}
</style>