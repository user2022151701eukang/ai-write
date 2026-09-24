<template>
  <div class="paper-edit">
    <!-- 顶部工具栏 -->
    <div class="toolbar app-card app-card--lg">
      <div class="toolbar-left">
        <h2 class="paper-title text-ellipsis" :title="paper?.title">
          {{ paper?.title || '加载中…' }}
        </h2>
        <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
      </div>

      <div class="toolbar-actions">
        <el-button type="primary" :loading="editorStore.generating" @click="handleStreamGenerate">
          🚀 AI 一键生成论文
        </el-button>
        <el-button type="danger" plain :disabled="!editorStore.generating" @click="handleStop">
          ⏹ 停止生成
        </el-button>
        <el-button :loading="editorStore.generating" @click="handleGenerateOutline">📋 生成大纲</el-button>
        <el-button @click="previewVisible = true">📄 全文预览</el-button>
        <el-button @click="versionVisible = true">🕒 版本管理</el-button>
        <el-dropdown trigger="click" @command="handleExport">
          <el-button :loading="exporting">📥 导出 ▾</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="docx">Word 文档（.docx）</el-dropdown-item>
              <el-dropdown-item command="pdf">PDF 文档（.pdf）</el-dropdown-item>
              <el-dropdown-item command="md">Markdown（.md）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="editorStore.generating || editorStore.progress > 0" class="progress-row">
        <el-progress :percentage="editorStore.progress" :stroke-width="10" striped />
        <span class="status-text">{{ editorStore.statusText }}</span>
      </div>
    </div>

    <!-- 三栏布局 -->
    <div class="workspace">
      <!-- 左栏：章节列表 -->
      <div class="col-left">
        <Sidebar
          :chapters="editorStore.chapters"
          :active-id="editorStore.currentChapter?.id"
          @select="handleSelectChapter"
          @add="handleAddChapter"
          @remove="handleRemoveChapter"
        />
      </div>

      <!-- 中栏：大纲 + 章节编辑 -->
      <div class="col-center">
        <el-collapse v-model="activeCollapse" class="outline-collapse">
          <el-collapse-item name="outline">
            <template #title>
              <span class="collapse-title">🗂️ 论文大纲</span>
            </template>
            <OutlineEditor
              v-model="outlineText"
              :generating="editorStore.generating"
              @generate="handleGenerateOutline"
              @save="handleSaveOutline"
            />
          </el-collapse-item>
        </el-collapse>

        <!-- 流式输出区域 -->
        <div v-if="editorStore.generating || editorStore.streamingText" class="stream-panel">
          <div class="stream-title">
            实时生成内容
            <span v-if="editorStore.streamingSection">· {{ editorStore.streamingSection }}</span>
          </div>
          <div ref="streamBoxRef" class="stream-text">{{ editorStore.streamingText || '等待模型输出…' }}</div>
          <div v-if="editorStore.logs.length" class="stream-logs">
            <div v-for="(log, index) in editorStore.logs" :key="index" class="log-item" :class="log.type">
              [{{ log.time }}] {{ log.message }}
            </div>
          </div>
        </div>

        <ChapterEditor
          :chapter="editorStore.currentChapter"
          :generating="editorStore.generating"
          @save="handleSaveChapter"
          @generate="handleGenerateChapter"
          @polish="handlePolishChapter"
        />
      </div>

      <!-- 右栏：参考文献 -->
      <div class="col-right">
        <ReferenceSearch :paper-id="paperId" @imported="fetchReferences" />
        <ReferenceList
          :references="references"
          :loading="referenceLoading"
          :paper-id="paperId"
          @remove="handleRemoveReference"
          @refresh="fetchReferences"
        />
      </div>
    </div>

    <!-- 全文预览 -->
    <el-dialog v-model="previewVisible" title="论文全文预览" width="72%" top="5vh">
      <PaperDetail :paper="paper" />
    </el-dialog>

    <!-- 版本管理 -->
    <el-drawer v-model="versionVisible" title="版本管理" size="58%">
      <VersionPanel :paper-id="paperId" @restored="handleVersionRestored" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import Sidebar from '@/components/common/Sidebar.vue'
import OutlineEditor from '@/components/paper/OutlineEditor.vue'
import ChapterEditor from '@/components/paper/ChapterEditor.vue'
import PaperDetail from '@/components/paper/PaperDetail.vue'
import VersionPanel from '@/components/paper/VersionPanel.vue'
import ReferenceSearch from '@/components/reference/ReferenceSearch.vue'
import ReferenceList from '@/components/reference/ReferenceList.vue'
import request from '@/api/request'
import { exportPaperFile } from '@/api/paper'
import type { ExportFormat } from '@/api/paper'
import { useEditorStore } from '@/stores/editor'
import type { Chapter, PolishFocus } from '@/api/chapter'

/** 文献 */
interface Reference {
  id: number
  paper_id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number
  abstract?: string
}

const route = useRoute()
const router = useRouter()
const editorStore = useEditorStore()

const paperId = Number(route.params.id)
const activeCollapse = ref<string[]>(['outline'])
const outlineText = ref('')
const references = ref<Reference[]>([])
const referenceLoading = ref(false)
const previewVisible = ref(false)
const exporting = ref(false)
const versionVisible = ref(false)
const streamBoxRef = ref<HTMLElement | null>(null)

const paper = computed(() => editorStore.paper)

/** 状态标签类型 */
const statusType = computed<'info' | 'warning' | 'primary' | 'success'>(() => {
  const map: Record<string, 'info' | 'warning' | 'primary' | 'success'> = {
    draft: 'info',
    outline: 'warning',
    writing: 'primary',
    review: 'warning',
    completed: 'success'
  }
  return map[paper.value?.status || 'draft'] || 'info'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    draft: '草稿',
    outline: '大纲阶段',
    writing: '撰写中',
    review: '审核中',
    completed: '已完成'
  }
  return map[paper.value?.status || 'draft'] || ''
})

/** 加载论文与章节 */
async function loadData() {
  if (!paperId || Number.isNaN(paperId)) {
    ElMessage.error('论文 ID 无效')
    router.push('/papers')
    return
  }
  try {
    const detail = await editorStore.fetchPaperAndChapters(paperId)
    outlineText.value = detail.outline || ''
    await fetchReferences()
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}

onMounted(loadData)

onUnmounted(() => {
  editorStore.stopStream()
})

// 流式文本自动滚动到底部
watch(
  () => editorStore.streamingText,
  async () => {
    await nextTick()
    if (streamBoxRef.value) {
      streamBoxRef.value.scrollTop = streamBoxRef.value.scrollHeight
    }
  }
)

/** 获取文献列表 */
async function fetchReferences() {
  referenceLoading.value = true
  try {
    const res = await request.get<any, Reference[]>('/references/', {
      params: { paper_id: paperId }
    })
    references.value = res || []
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    referenceLoading.value = false
  }
}

/** 选择章节 */
function handleSelectChapter(chapter: Chapter) {
  editorStore.setCurrentChapter(chapter)
}

/** 新增章节 */
async function handleAddChapter() {
  await editorStore.addChapter()
}

/** 删除章节 */
async function handleRemoveChapter(id: number) {
  await editorStore.removeChapter(id)
}

/** 保存章节 */
async function handleSaveChapter(payload: { title: string; content: string }) {
  const chapter = editorStore.currentChapter
  if (!chapter) return
  await editorStore.saveChapter({ ...chapter, title: payload.title }, payload.content)
}

/** AI 撰写章节 */
async function handleGenerateChapter() {
  const chapter = editorStore.currentChapter
  if (!chapter) {
    ElMessage.warning('请先选择章节')
    return
  }
  try {
    await editorStore.generateChapter(chapter.id, {
      word_count: paper.value?.word_limit ? Math.round(paper.value.word_limit / 8) : 1500,
      use_references: true
    })
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}

/** AI 润色章节 */
async function handlePolishChapter(focus: PolishFocus) {
  const chapter = editorStore.currentChapter
  if (!chapter) {
    ElMessage.warning('请先选择章节')
    return
  }
  try {
    await editorStore.polishChapter(chapter.id, focus)
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}

/** 流式生成论文 */
async function handleStreamGenerate() {
  await editorStore.generateStream(paperId, {
    paper_type: paper.value?.paper_type,
    word_limit: paper.value?.word_limit,
    is_topic_clear: true,
    polish: true
  })
  outlineText.value = editorStore.paper?.outline || outlineText.value
}

/** 停止生成 */
function handleStop() {
  editorStore.stopStream()
}

/** 生成大纲（同步接口） */
async function handleGenerateOutline() {
  const text = await editorStore.generateOutline()
  if (text) {
    outlineText.value = text
    ElMessage.success('大纲生成完成，记得点击保存')
  }
}

/** 保存大纲 */
async function handleSaveOutline() {
  if (!outlineText.value) {
    ElMessage.warning('大纲内容为空')
    return
  }
  try {
    JSON.parse(outlineText.value)
  } catch (e) {
    ElMessage.warning('大纲 JSON 格式有误，请检查后再保存')
    return
  }
  await editorStore.saveOutline(outlineText.value)
}

/** 删除文献 */
async function handleRemoveReference(id: number) {
  await request.delete(`/references/${id}`)
  ElMessage.success('文献已删除')
  fetchReferences()
}

/** 版本回滚成功后重新加载论文数据 */
async function handleVersionRestored() {
  await loadData()
  outlineText.value = editorStore.paper?.outline || ''
  ElMessage.success('已回滚，内容已更新')
}

/** 导出论文：Markdown 在前端生成，Word / PDF 由后端生成 */
async function handleExport(format: ExportFormat) {
  const paperId = editorStore.paper?.id
  if (!paperId) {
    ElMessage.warning('论文尚未加载')
    return
  }
  const filename = paper.value?.title || 'paper'

  if (format === 'md') {
    const content = paper.value?.content || ''
    if (!content) {
      ElMessage.warning('暂无内容可导出')
      return
    }
    downloadBlob(new Blob([content], { type: 'text/markdown;charset=utf-8' }), `${filename}.md`)
    ElMessage.success('已开始下载 Markdown 文件')
    return
  }

  exporting.value = true
  try {
    const blob = await exportPaperFile(paperId, format)
    downloadBlob(blob, `${filename}.${format}`)
    ElMessage.success(`已导出 ${format.toUpperCase()} 文件`)
  } catch (error) {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    exporting.value = false
  }
}

/** 触发浏览器下载 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<style scoped lang="scss">
.paper-edit {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.toolbar {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 240px;

  .paper-title {
    font-size: 18px;
    font-weight: 700;
    max-width: 420px;
  }
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.progress-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;

  .status-text {
    font-size: 13px;
    color: var(--text-secondary);
    white-space: nowrap;
  }

  :deep(.el-progress) {
    flex: 1;
  }
}

.workspace {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;

  @media (max-width: 1280px) {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  @media (max-width: 960px) {
    grid-template-columns: minmax(0, 1fr);
  }
}

.col-left {
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 120px);
}

.col-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.col-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.outline-collapse {
  border: none;

  :deep(.el-collapse-item__header) {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 0 14px;
    font-weight: 600;
    height: 46px;
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding-bottom: 0;
  }
}

.collapse-title {
  font-size: 14px;
}

.stream-logs {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
  max-height: 140px;
  overflow-y: auto;

  .log-item {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.7;

    &.success {
      color: #10b981;
    }

    &.warning {
      color: #e6a23c;
    }

    &.error {
      color: #f56c6c;
    }
  }
}
</style>