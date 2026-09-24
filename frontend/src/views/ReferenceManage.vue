<template>
  <div class="page-container">
    <!-- 向量库状态 -->
    <div class="status-card app-card app-card--lg">
      <div class="status-left">
        <div class="status-title">🗄️ 向量库状态</div>
        <div class="status-items">
          <span class="status-item">
            文献总数：<b>{{ status.vector_count }}</b>
          </span>
          <span class="status-item">
            大模型：
            <el-tag :type="status.llm_configured ? 'success' : 'danger'" size="small">
              {{ status.llm_configured ? '已配置' : '未配置' }}
            </el-tag>
          </span>
          <span class="status-item">
            Embedding：
            <el-tag :type="status.embedding_configured ? 'success' : 'danger'" size="small">
              {{ status.embedding_configured ? '已配置' : '未配置' }}
            </el-tag>
          </span>
        </div>
        <div v-if="!status.llm_configured || !status.embedding_configured" class="status-tip">
          ⚠️ 检测到模型未配置，请前往 backend/.env 填写 QWEN_API_KEY 与 Embedding 相关配置后重启后端
        </div>
      </div>
      <el-button type="primary" :loading="rebuilding" @click="handleRebuild">🔄 重建向量库</el-button>
    </div>

    <!-- 检索 -->
    <ReferenceSearch @imported="fetchReferences" />

    <!-- 列表 -->
    <ReferenceList
      :references="references"
      :loading="loading"
      @remove="handleRemove"
      @refresh="fetchReferences"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ReferenceSearch from '@/components/reference/ReferenceSearch.vue'
import ReferenceList from '@/components/reference/ReferenceList.vue'
import request from '@/api/request'

/** 文献 */
interface Reference {
  id: number
  paper_id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number
}

interface VectorStatus {
  vector_count: number
  llm_configured: boolean
  embedding_configured: boolean
}

const references = ref<Reference[]>([])
const loading = ref(false)
const rebuilding = ref(false)
const status = reactive<VectorStatus>({
  vector_count: 0,
  llm_configured: false,
  embedding_configured: false
})

onMounted(() => {
  fetchReferences()
  fetchStatus()
})

/** 获取文献列表 */
async function fetchReferences() {
  loading.value = true
  try {
    const res = await request.get<any, Reference[]>('/references/', { params: { limit: 100 } })
    references.value = res || []
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    loading.value = false
  }
}

/** 获取向量库状态 */
async function fetchStatus() {
  try {
    const res = await request.get<any, VectorStatus>('/references/status')
    Object.assign(status, res)
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}

/** 删除文献 */
async function handleRemove(id: number) {
  await request.delete(`/references/${id}`)
  ElMessage.success('文献已删除')
  fetchReferences()
  fetchStatus()
}

/** 重建向量库 */
async function handleRebuild() {
  rebuilding.value = true
  try {
    const res = await request.post<any, { message: string; count: number }>(
      '/references/rebuild-vector-store'
    )
    ElMessage.success(res?.message || `向量库已重建，共 ${res?.count ?? 0} 条`)
    fetchStatus()
  } finally {
    rebuilding.value = false
  }
}
</script>

<style scoped lang="scss">
.page-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-card {
  padding: 20px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.status-left {
  flex: 1;
  min-width: 280px;
}

.status-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 10px;
}

.status-items {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
  font-size: 14px;
  color: var(--text-secondary);

  b {
    color: var(--primary-color);
    font-size: 16px;
  }
}

.status-tip {
  margin-top: 12px;
  font-size: 13px;
  color: #e6a23c;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 8px;
  padding: 8px 12px;
}
</style>