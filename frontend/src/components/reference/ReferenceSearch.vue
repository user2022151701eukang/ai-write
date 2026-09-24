<template>
  <div class="reference-search">
    <div class="search-header">🔍 语义文献检索</div>

    <div class="search-form">
      <el-input
        v-model="query"
        placeholder="输入检索词，如：多 Agent 协作 论文写作"
        clearable
        @keyup.enter="handleSearch"
      />
      <div class="form-row">
        <span class="label">Top K</span>
        <el-input-number v-model="topK" :min="1" :max="20" size="small" controls-position="right" />
        <span class="label">引用格式</span>
        <el-select v-model="format" size="small" style="width: 110px">
          <el-option label="GB/T 7714" value="gbt" />
          <el-option label="APA" value="apa" />
          <el-option label="MLA" value="mla" />
        </el-select>
        <el-button type="primary" size="small" :loading="loading" @click="handleSearch">
          🔍 语义检索
        </el-button>
      </div>
    </div>

    <div v-if="results.length" class="result-list">
      <div v-for="item in results" :key="item.id ?? item.title" class="result-item">
        <div class="result-head">
          <span class="result-title">{{ item.title }}</span>
          <span class="result-score">{{ formatScore(item.score) }}</span>
        </div>
        <div class="result-meta">
          {{ item.authors || '未知作者' }} · {{ item.journal || '未知期刊' }} · {{ item.year || '-' }}
        </div>
        <div v-if="item.citation" class="result-citation">📎 {{ item.citation }}</div>
        <div class="result-actions">
          <el-button size="small" type="primary" plain :loading="importing === item.title" @click="handleImport(item)">
            加入文献库
          </el-button>
        </div>
      </div>
    </div>

    <div v-else-if="searched" class="empty-tip">未检索到相关文献</div>

    <div v-if="formatted" class="formatted-box">
      <div class="formatted-head">
        <span>📋 编号引用列表</span>
        <el-button size="small" text type="primary" @click="handleCopy">复制</el-button>
      </div>
      <pre class="formatted-text">{{ formatted }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

/** 检索结果条目 */
interface SearchResultItem {
  id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number
  score?: number
  citation?: string
}

interface SearchResponse {
  query: string
  references: SearchResultItem[]
  formatted: string
}

const props = defineProps<{
  paperId?: number
}>()

const emit = defineEmits<{
  (e: 'imported'): void
}>()

const query = ref('')
const topK = ref(5)
const format = ref<'gbt' | 'apa' | 'mla'>('gbt')
const loading = ref(false)
const searched = ref(false)
const importing = ref('')
const results = ref<SearchResultItem[]>([])
const formatted = ref('')

/** 相似度百分比展示 */
function formatScore(score?: number): string {
  if (score === undefined || score === null) return ''
  const value = score <= 1 ? score * 100 : score
  return `相似度 ${value.toFixed(1)}%`
}

/** 语义检索 */
async function handleSearch() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入检索词')
    return
  }
  loading.value = true
  try {
    const res = await request.post<any, SearchResponse>('/references/search', {
      query: query.value,
      top_k: topK.value,
      format: format.value
    })
    results.value = res.references || []
    formatted.value = res.formatted || ''
    searched.value = true
  } finally {
    loading.value = false
  }
}

/** 将检索结果加入文献库 */
async function handleImport(item: SearchResultItem) {
  importing.value = item.title
  try {
    await request.post('/references/', {
      title: item.title,
      authors: item.authors || '',
      journal: item.journal || '',
      year: item.year || undefined,
      paper_id: props.paperId || undefined
    })
    ElMessage.success('已加入文献库')
    emit('imported')
  } finally {
    importing.value = ''
  }
}

/** 复制编号引用列表 */
async function handleCopy() {
  try {
    await navigator.clipboard.writeText(formatted.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}
</script>

<style scoped lang="scss">
.reference-search {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-header {
  font-weight: 600;
  font-size: 14px;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  .label {
    font-size: 13px;
    color: var(--text-secondary);
  }
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

.result-item {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px;
  background: #fbfcfe;
}

.result-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
}

.result-score {
  font-size: 12px;
  color: #10b981;
  flex-shrink: 0;
}

.result-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.result-citation {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
  line-height: 1.6;
}

.result-actions {
  margin-top: 8px;
}

.empty-tip {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 16px 0;
}

.formatted-box {
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}

.formatted-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.formatted-text {
  max-height: 200px;
  overflow-y: auto;
  background: #f7f8fb;
  border-radius: 8px;
  padding: 10px;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
}
</style>