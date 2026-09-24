<template>
  <div class="version-panel">
    <!-- 顶部：手动保存版本 -->
    <div class="create-row">
      <el-input
        v-model="description"
        placeholder="版本说明，如：完成第三章初稿"
        clearable
        @keyup.enter="handleSave"
      />
      <el-button type="primary" :loading="saving" @click="handleSave">💾 保存版本</el-button>
    </div>

    <!-- 版本列表 -->
    <div v-loading="loading" class="version-list">
      <div v-if="!loading && !versions.length" class="empty-tip">
        暂无版本记录，点击右上角保存第一个版本
      </div>

      <div v-for="version in versions" :key="version.id" class="version-item">
        <div class="item-main">
          <div class="item-head">
            <span class="version-no">v{{ version.version_number }}</span>
            <el-tag :type="typeTagType(version.version_type)" size="small">
              {{ typeLabel(version.version_type) }}
            </el-tag>
            <span class="version-time">{{ formatDate(version.created_at) }}</span>
          </div>
          <div class="item-desc">{{ version.description || '（无版本说明）' }}</div>
          <div class="item-meta">
            <span>📑 {{ version.chapter_count }} 章</span>
            <span>📚 {{ version.reference_count }} 篇文献</span>
            <span>✍️ {{ version.word_count }} 字</span>
            <span v-if="version.trigger_node" class="trigger-node">触发节点：{{ version.trigger_node }}</span>
          </div>
        </div>
        <div class="item-actions">
          <el-button size="small" @click="openDetail(version)">详情</el-button>
          <el-button size="small" @click="openDiff(version)">对比</el-button>
          <el-button size="small" type="warning" plain @click="handleRollback(version)">回滚</el-button>
        </div>
      </div>
    </div>

    <!-- 版本详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="760px" top="6vh">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <div class="detail-section">
            <div class="section-label">论文标题</div>
            <div class="section-text">{{ detail.snapshot.paper.title || '-' }}</div>
          </div>
          <div class="detail-section">
            <div class="section-label">摘要</div>
            <div class="section-text pre-wrap">{{ detail.snapshot.paper.abstract || '暂无摘要' }}</div>
          </div>
          <div class="detail-section">
            <div class="section-label">关键词</div>
            <div class="section-text">{{ detail.snapshot.paper.keywords || '暂无关键词' }}</div>
          </div>
          <div class="detail-section">
            <div class="section-label">字数</div>
            <div class="section-text">{{ detail.word_count }} 字</div>
          </div>

          <div class="detail-section">
            <div class="section-label">大纲小节（{{ outlineSections.length }}）</div>
            <div v-if="outlineSections.length" class="outline-list">
              <div v-for="(section, index) in outlineSections" :key="index" class="outline-item">
                <span class="outline-index">{{ index + 1 }}</span>
                <span class="outline-title">{{ section.title }}</span>
                <span class="outline-words">约 {{ section.word_count || 0 }} 字</span>
              </div>
            </div>
            <div v-else class="empty-line">暂无大纲内容</div>
          </div>

          <div class="detail-section">
            <div class="section-label">章节（{{ detail.snapshot.chapters.length }}）</div>
            <div v-if="detail.snapshot.chapters.length" class="chapter-list">
              <div v-for="(chapter, index) in detail.snapshot.chapters" :key="index" class="chapter-item">
                <div class="chapter-head">
                  <span class="chapter-title">{{ chapter.title }}</span>
                  <span class="chapter-words">{{ chapter.word_count }} 字</span>
                </div>
                <div class="chapter-preview">{{ previewText(chapter.content) }}</div>
              </div>
            </div>
            <div v-else class="empty-line">暂无章节内容</div>
          </div>

          <div class="detail-section">
            <div class="section-label">参考文献（{{ detail.snapshot.references.length }}）</div>
            <div v-if="detail.snapshot.references.length" class="ref-list">
              <div v-for="(ref, index) in detail.snapshot.references" :key="index" class="ref-item">
                <span class="ref-title">{{ ref.title }}</span>
                <span class="ref-meta">{{ ref.authors || '佚名' }}{{ ref.year ? ` · ${ref.year}` : '' }}</span>
              </div>
            </div>
            <div v-else class="empty-line">暂无参考文献</div>
          </div>
        </template>
      </div>
    </el-dialog>

    <!-- 版本对比弹窗 -->
    <el-dialog v-model="diffVisible" :title="diffTitle" width="80%" top="6vh">
      <div v-loading="diffLoading" class="diff-body">
        <VersionDiff :diff="currentDiff" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import VersionDiff from './VersionDiff.vue'
import {
  createVersion,
  diffVersion,
  getVersionDetail,
  getVersions,
  rollbackVersion
} from '@/api/version'
import type { VersionDetail, VersionDiff as VersionDiffType, VersionSummary, VersionType } from '@/api/version'

const props = defineProps<{
  paperId: number
}>()

const emit = defineEmits<{
  (e: 'restored'): void
}>()

/** 大纲小节（详情弹窗展示用） */
interface OutlineSectionBrief {
  title: string
  word_count?: number
}

const versions = ref<VersionSummary[]>([])
const loading = ref(false)
const description = ref('')
const saving = ref(false)

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<VersionDetail | null>(null)

const diffVisible = ref(false)
const diffLoading = ref(false)
const currentDiff = ref<VersionDiffType | null>(null)

/** 详情弹窗标题 */
const detailTitle = computed(() =>
  detail.value ? `版本详情 · v${detail.value.version_number}` : '版本详情'
)

/** 对比弹窗标题 */
const diffTitle = computed(() => {
  const d = currentDiff.value
  if (!d) return '版本对比'
  return `${d.left.label} ↔ ${d.right.label}`
})

/** 从快照中容错解析大纲小节 */
const outlineSections = computed<OutlineSectionBrief[]>(() => {
  const raw = detail.value?.snapshot.paper.outline
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    const list = Array.isArray(parsed) ? parsed : parsed?.sections || []
    return (list as OutlineSectionBrief[]) || []
  } catch (e) {
    return []
  }
})

/** 版本类型标签颜色 */
function typeTagType(type: VersionType): 'primary' | 'success' | 'warning' | 'info' {
  const map: Record<VersionType, 'primary' | 'success' | 'warning' | 'info'> = {
    manual: 'primary',
    auto: 'success',
    rollback: 'warning',
    backup: 'info'
  }
  return map[type] || 'info'
}

/** 版本类型文案 */
function typeLabel(type: VersionType): string {
  const map: Record<VersionType, string> = {
    manual: '手动',
    auto: '自动',
    rollback: '回滚',
    backup: '回滚前备份'
  }
  return map[type] || type
}

/** 本地化时间显示 */
function formatDate(value: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

/** 内容前 200 字预览 */
function previewText(content: string): string {
  const text = content || ''
  if (text.length <= 200) return text || '（无正文内容）'
  return `${text.slice(0, 200)}…`
}

/** 加载版本列表 */
async function loadVersions() {
  loading.value = true
  try {
    const res = await getVersions(props.paperId)
    versions.value = res || []
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    loading.value = false
  }
}

onMounted(loadVersions)

/** 手动保存版本 */
async function handleSave() {
  if (!description.value.trim()) {
    ElMessage.warning('请填写版本说明')
    return
  }
  saving.value = true
  try {
    await createVersion(props.paperId, description.value.trim())
    ElMessage.success('版本保存成功')
    description.value = ''
    await loadVersions()
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    saving.value = false
  }
}

/** 打开版本详情 */
async function openDetail(version: VersionSummary) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getVersionDetail(props.paperId, version.id)
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    detailLoading.value = false
  }
}

/** 打开版本对比（该版本 vs 当前内容） */
async function openDiff(version: VersionSummary) {
  diffVisible.value = true
  diffLoading.value = true
  currentDiff.value = null
  try {
    currentDiff.value = await diffVersion(props.paperId, version.id)
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    diffLoading.value = false
  }
}

/** 回滚到指定版本 */
async function handleRollback(version: VersionSummary) {
  try {
    await ElMessageBox.confirm(
      `确定回滚到 v${version.version_number} 吗？历史版本不会删除，系统会先自动备份当前内容，再生成一个回滚版本。`,
      '回滚确认',
      {
        confirmButtonText: '确定回滚',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch (e) {
    // 用户取消
    return
  }
  try {
    const res = await rollbackVersion(props.paperId, version.id)
    ElMessage.success(
      `已回滚到 v${res.target_version_number}，当前内容已备份为 v${res.backup_version_number}，并生成回滚版本 v${res.rollback_version_number}`
    )
    await loadVersions()
    emit('restored')
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}
</script>

<style scoped lang="scss">
.version-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.create-row {
  display: flex;
  gap: 10px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}

.empty-tip {
  color: var(--text-secondary);
  font-size: 14px;
  padding: 40px 0;
  text-align: center;
}

.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  transition: all 0.25s ease;

  &:hover {
    box-shadow: 0 6px 18px rgba(102, 126, 234, 0.12);
  }
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;

  .version-no {
    font-size: 15px;
    font-weight: 700;
    color: var(--primary-color);
  }

  .version-time {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.item-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-primary);
}

.item-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-secondary);
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 详情弹窗 */
.detail-body {
  min-height: 120px;
  max-height: 68vh;
  overflow-y: auto;
  padding-right: 6px;
}

.detail-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
}

.section-text {
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-word;

  &.pre-wrap {
    white-space: pre-wrap;
  }
}

.outline-list,
.chapter-list,
.ref-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.outline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .outline-index {
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

  .outline-title {
    font-weight: 600;
  }

  .outline-words {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.chapter-item {
  border-left: 3px solid rgba(102, 126, 234, 0.35);
  padding-left: 10px;
}

.chapter-head {
  display: flex;
  align-items: center;
  gap: 10px;

  .chapter-title {
    font-size: 13px;
    font-weight: 600;
  }

  .chapter-words {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.chapter-preview {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.7;
  word-break: break-word;
}

.ref-item {
  display: flex;
  flex-direction: column;
  font-size: 13px;

  .ref-title {
    font-weight: 600;
  }

  .ref-meta {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.empty-line {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 对比弹窗 */
.diff-body {
  min-height: 160px;
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 6px;
}
</style>