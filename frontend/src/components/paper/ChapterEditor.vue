<template>
  <div class="chapter-editor">
    <template v-if="chapter">
      <div class="toolbar">
        <el-input
          v-model="title"
          class="title-input"
          size="default"
          placeholder="章节标题"
        />
        <div class="toolbar-actions">
          <el-button type="success" size="small" :loading="generating" @click="emit('generate')">
            🤖 AI 撰写本章
          </el-button>
          <el-dropdown :disabled="generating" @command="handlePolish">
            <el-button type="warning" size="small" :loading="generating">
              ✨ AI 润色
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="language">语言润色</el-dropdown-item>
                <el-dropdown-item command="logic">逻辑优化</el-dropdown-item>
                <el-dropdown-item command="format">格式规范</el-dropdown-item>
                <el-dropdown-item command="all">全面润色</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="primary" size="small" @click="handleSave">💾 保存</el-button>
        </div>
      </div>

      <Editor v-model="content" height="520px" @save="handleSave" />

      <div class="footer-info">
        <span>字数：{{ wordCount }}</span>
        <span>最后更新：{{ formatDate(chapter.updated_at) }}</span>
      </div>
    </template>

    <div v-else class="empty-state">
      <div class="empty-icon">📝</div>
      <div class="empty-text">请从左侧选择章节，或点击「+ 新增章节」开始撰写</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import Editor from '@/components/common/Editor.vue'
import type { Chapter, PolishFocus } from '@/api/chapter'

const props = defineProps<{
  chapter: Chapter | null
  generating?: boolean
}>()

const emit = defineEmits<{
  (e: 'save', payload: { title: string; content: string }): void
  (e: 'generate'): void
  (e: 'polish', focus: PolishFocus): void
}>()

const title = ref('')
const content = ref('')

// 章节切换时同步本地编辑内容
watch(
  () => props.chapter,
  (chapter) => {
    title.value = chapter?.title || ''
    content.value = chapter?.content || ''
  },
  { immediate: true }
)

// 外部内容变化（如 AI 生成完成）时同步
watch(
  () => [props.chapter?.content, props.chapter?.title],
  () => {
    if (!props.chapter) return
    if (props.chapter.content !== content.value && props.chapter.content) {
      content.value = props.chapter.content
    }
    if (props.chapter.title !== title.value && props.chapter.title) {
      title.value = props.chapter.title
    }
  }
)

const wordCount = computed(() => (content.value || '').replace(/\s/g, '').length)

function formatDate(value: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

/** 保存当前章节 */
function handleSave() {
  emit('save', { title: title.value, content: content.value })
}

/** 润色命令 */
function handlePolish(command: string | number | object) {
  emit('polish', command as PolishFocus)
}
</script>

<style scoped lang="scss">
.chapter-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.title-input {
  flex: 1;
  min-width: 200px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.footer-info {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 0 4px;
}

.empty-state {
  background: var(--card-bg);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  padding: 80px 20px;
  text-align: center;

  .empty-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }

  .empty-text {
    color: var(--text-secondary);
    font-size: 14px;
  }
}
</style>