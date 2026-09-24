<template>
  <div class="md-editor">
    <el-tabs v-model="activeTab" class="editor-tabs">
      <el-tab-pane label="编辑" name="edit">
        <textarea
          v-model="innerValue"
          class="editor-textarea"
          :style="{ height: height || '460px' }"
          :readonly="readonly"
          placeholder="在此输入 Markdown 正文…"
        ></textarea>
      </el-tab-pane>
      <el-tab-pane label="预览" name="preview">
        <div
          ref="previewRef"
          class="markdown-body editor-preview"
          :style="{ minHeight: height || '460px' }"
          v-html="html"
        ></div>
      </el-tab-pane>
    </el-tabs>

    <div class="editor-footer">
      <span class="word-count">字数：{{ wordCount }}</span>
      <el-button v-if="!readonly" type="primary" size="small" @click="handleSave">保存</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  modelValue: string
  height?: string
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'save'): void
}>()

const activeTab = ref('edit')
const previewRef = ref<HTMLElement | null>(null)

const innerValue = computed({
  get: () => props.modelValue || '',
  set: (value: string) => emit('update:modelValue', value)
})

/** 渲染 Markdown */
const html = computed(() => {
  try {
    return marked.parse(props.modelValue || '') as string
  } catch (e) {
    return '<p>内容解析失败</p>'
  }
})

/** 统计字数（去空白） */
const wordCount = computed(() => (props.modelValue || '').replace(/\s/g, '').length)

/** 预览时对代码块做语法高亮 */
watch([activeTab, html], async () => {
  if (activeTab.value !== 'preview') return
  await nextTick()
  const blocks = previewRef.value?.querySelectorAll('pre code') || []
  blocks.forEach((block) => {
    hljs.highlightElement(block as HTMLElement)
  })
})

function handleSave() {
  emit('save')
}
</script>

<style scoped lang="scss">
.md-editor {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.editor-tabs {
  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 14px;
    border-bottom: 1px solid var(--border-color);
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }
}

.editor-textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: vertical;
  padding: 14px 16px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  background: transparent;
}

.editor-preview {
  padding: 14px 16px;
  overflow-y: auto;
  max-height: 620px;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-top: 1px solid var(--border-color);
  background: #fafbfd;

  .word-count {
    font-size: 13px;
    color: var(--text-secondary);
  }
}
</style>