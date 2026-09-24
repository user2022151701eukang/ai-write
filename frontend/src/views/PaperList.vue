<template>
  <div class="page-container">
    <div class="page-head">
      <div class="stats">
        <div class="stat-card app-card">
          <div class="stat-value">{{ paperStore.paperCount }}</div>
          <div class="stat-label">论文总数</div>
        </div>
        <div class="stat-card app-card">
          <div class="stat-value">{{ paperStore.draftCount }}</div>
          <div class="stat-label">草稿</div>
        </div>
        <div class="stat-card app-card">
          <div class="stat-value">{{ paperStore.completedCount }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      <el-button type="primary" @click="router.push('/papers/create')">+ 创建新论文</el-button>
    </div>

    <div v-loading="paperStore.loading" class="list-wrap">
      <PaperCardList
        :papers="paperStore.papers"
        @edit="handleEdit"
        @generate="handleGenerate"
        @remove="handleRemove"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PaperCardList from '@/components/paper/PaperList.vue'
import { usePaperStore } from '@/stores/paper'

const router = useRouter()
const paperStore = usePaperStore()

onMounted(() => {
  paperStore.fetchPapers()
})

/** 跳转编辑工作台 */
function handleEdit(id: number) {
  router.push(`/papers/${id}/edit`)
}

/** 一键生成论文 */
async function handleGenerate(id: number) {
  ElMessage.info('已开始生成，请稍候…')
  try {
    await paperStore.generatePaper(id)
    ElMessage.success('生成完成')
    paperStore.fetchPapers()
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}

/** 删除论文 */
async function handleRemove(id: number) {
  try {
    await paperStore.deletePaper(id)
    ElMessage.success('删除成功')
  } catch (e) {
    // 错误已由拦截器统一提示
  }
}
</script>

<style scoped lang="scss">
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
  flex-wrap: wrap;
}

.stats {
  display: flex;
  gap: 16px;
}

.stat-card {
  min-width: 150px;
  padding: 16px 20px;

  .stat-value {
    font-size: 26px;
    font-weight: 700;
    color: var(--primary-color);
    line-height: 1.2;
  }

  .stat-label {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
  }
}

.list-wrap {
  min-height: 200px;
}
</style>