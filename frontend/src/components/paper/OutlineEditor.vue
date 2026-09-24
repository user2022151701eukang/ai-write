<template>
  <div class="outline-editor">
    <div class="editor-header">
      <span class="header-title">🗂️ 大纲编辑器</span>
      <div class="header-actions">
        <el-button type="success" size="small" :loading="generating" @click="emit('generate')">
          🤖 AI 生成大纲
        </el-button>
        <el-button type="primary" size="small" @click="emit('save')">保存大纲</el-button>
      </div>
    </div>

    <div class="editor-body">
      <template v-if="!parseFailed">
        <div class="outline-title-row">
          <span class="label">大纲标题</span>
          <el-input v-model="outlineTitle" size="small" placeholder="请输入大纲标题" @change="sync" />
        </div>

        <div
          v-for="(section, index) in sections"
          :key="index"
          class="section-row"
        >
          <div class="row-head">
            <span class="section-index">{{ index + 1 }}</span>
            <el-input
              v-model="section.title"
              size="small"
              class="section-title-input"
              placeholder="章节标题"
              @change="sync"
            />
            <el-input-number
              v-model="section.word_count"
              size="small"
              :min="0"
              :step="500"
              controls-position="right"
              class="word-input"
              @change="sync"
            />
            <div class="row-buttons">
              <el-button size="small" text :disabled="index === 0" @click="moveUp(index)">上移</el-button>
              <el-button
                size="small"
                text
                :disabled="index === sections.length - 1"
                @click="moveDown(index)"
              >
                下移
              </el-button>
              <el-button size="small" text type="danger" @click="removeSection(index)">删除</el-button>
            </div>
          </div>

          <div class="points-row">
            <el-tag
              v-for="(point, pi) in section.points"
              :key="pi"
              closable
              size="small"
              class="point-tag"
              @close="removePoint(index, pi)"
            >
              {{ point }}
            </el-tag>
            <el-input
              v-model="pointInputs[index]"
              size="small"
              class="point-input"
              placeholder="输入要点后回车添加"
              @keyup.enter="addPoint(index)"
            />
          </div>
        </div>

        <el-button class="add-section-btn" size="small" @click="addSection">+ 新增章节</el-button>
      </template>

      <template v-else>
        <el-alert
          title="大纲 JSON 解析失败，可直接编辑下方原始文本"
          type="warning"
          :closable="false"
          show-icon
          class="parse-alert"
        />
        <textarea v-model="rawText" class="raw-textarea" @input="onRawInput"></textarea>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { OutlineSection } from '@/api/paper'

const props = defineProps<{
  modelValue: string
  generating?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'generate'): void
  (e: 'save'): void
}>()

const parseFailed = ref(false)
const outlineTitle = ref('')
const sections = ref<OutlineSection[]>([])
const pointInputs = ref<string[]>([])
const rawText = ref('')
/** 由本组件自身触发的更新，避免重复解析 */
let selfUpdating = false

/** 同步内部输入容器长度 */
function ensurePointInputs() {
  if (pointInputs.value.length !== sections.value.length) {
    pointInputs.value = sections.value.map((_, i) => pointInputs.value[i] || '')
  }
}

/** 从 props 解析大纲 */
function parseFromProp(value: string) {
  const text = value || ''
  rawText.value = text
  if (!text.trim()) {
    parseFailed.value = false
    outlineTitle.value = ''
    sections.value = []
    pointInputs.value = []
    return
  }
  try {
    const parsed: any = JSON.parse(text)
    const list: OutlineSection[] = Array.isArray(parsed) ? parsed : parsed?.sections || []
    if (!Array.isArray(list)) throw new Error('格式错误')
    outlineTitle.value = parsed?.title || ''
    sections.value = list.map((item) => ({
      title: item?.title || '',
      points: Array.isArray(item?.points) ? [...item.points] : [],
      word_count: Number(item?.word_count) || 0
    }))
    ensurePointInputs()
    parseFailed.value = false
  } catch (e) {
    parseFailed.value = true
  }
}

/** 将内部结构回传为 JSON 字符串 */
function sync() {
  if (parseFailed.value) return
  selfUpdating = true
  const payload: any = { sections: sections.value }
  if (outlineTitle.value) payload.title = outlineTitle.value
  emit('update:modelValue', JSON.stringify(payload, null, 2))
}

function onRawInput() {
  selfUpdating = true
  emit('update:modelValue', rawText.value)
}

watch(
  () => props.modelValue,
  (value) => {
    if (selfUpdating) {
      selfUpdating = false
      return
    }
    parseFromProp(value)
  },
  { immediate: true }
)

/** 上移章节 */
function moveUp(index: number) {
  if (index === 0) return
  const list = sections.value
  ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
  sync()
}

/** 下移章节 */
function moveDown(index: number) {
  const list = sections.value
  if (index === list.length - 1) return
  ;[list[index + 1], list[index]] = [list[index], list[index + 1]]
  sync()
}

/** 删除章节 */
function removeSection(index: number) {
  sections.value.splice(index, 1)
  pointInputs.value.splice(index, 1)
  sync()
}

/** 新增章节 */
function addSection() {
  sections.value.push({ title: `第 ${sections.value.length + 1} 章`, points: [], word_count: 0 })
  pointInputs.value.push('')
  sync()
}

/** 添加要点 */
function addPoint(index: number) {
  const value = (pointInputs.value[index] || '').trim()
  if (!value) return
  sections.value[index].points.push(value)
  pointInputs.value[index] = ''
  sync()
}

/** 删除要点 */
function removePoint(index: number, pointIndex: number) {
  sections.value[index].points.splice(pointIndex, 1)
  sync()
}
</script>

<style scoped lang="scss">
.outline-editor {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);

  .header-title {
    font-weight: 600;
    font-size: 14px;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.editor-body {
  padding: 14px;
  max-height: 460px;
  overflow-y: auto;
}

.outline-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;

  .label {
    font-size: 13px;
    color: var(--text-secondary);
    width: 60px;
    flex-shrink: 0;
  }
}

.section-row {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
  background: #fbfcfe;
}

.row-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-index {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: rgba(102, 126, 234, 0.15);
  color: var(--primary-color);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.section-title-input {
  flex: 1;
  min-width: 120px;
}

.word-input {
  width: 130px;
  flex-shrink: 0;
}

.row-buttons {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.points-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding-left: 28px;
}

.point-tag {
  margin: 0;
}

.point-input {
  width: 220px;
}

.add-section-btn {
  width: 100%;
  border-style: dashed;
}

.parse-alert {
  margin-bottom: 10px;
}

.raw-textarea {
  width: 100%;
  min-height: 260px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  outline: none;
  resize: vertical;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 13px;
  line-height: 1.8;
}
</style>