<template>
  <div class="reference-list">
    <div class="list-header">
      <span class="header-title">📚 文献列表（{{ references.length }}）</span>
      <el-button size="small" type="primary" plain @click="dialogVisible = true">
        + 手动添加文献
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="references"
      size="small"
      class="ref-table"
      :empty-text="'暂无文献，可在上方检索或手动添加'"
    >
      <el-table-column prop="title" label="标题" min-width="220">
        <template #default="{ row }">
          <el-tooltip :content="row.title" placement="top" :disabled="!row.title">
            <span class="cell-ellipsis">{{ row.title }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="authors" label="作者" width="150">
        <template #default="{ row }">
          <el-tooltip :content="row.authors || '-'" placement="top">
            <span class="cell-ellipsis">{{ row.authors || '-' }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="journal" label="期刊" width="150">
        <template #default="{ row }">
          <span class="cell-ellipsis">{{ row.journal || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="year" label="年份" width="80" align="center">
        <template #default="{ row }">{{ row.year || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" align="center">
        <template #default="{ row }">
          <el-popconfirm
            title="确定删除该文献吗？"
            confirm-button-text="确定"
            cancel-button-text="取消"
            @confirm="handleRemove(row.id)"
          >
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手动添加文献 -->
    <el-dialog v-model="dialogVisible" title="手动添加文献" width="520px">
      <el-form :model="form" label-width="72px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="请输入文献标题" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="form.authors" placeholder="如：张三, 李四" />
        </el-form-item>
        <el-form-item label="期刊">
          <el-input v-model="form.journal" placeholder="请输入期刊名称" />
        </el-form-item>
        <el-form-item label="年份">
          <el-input-number v-model="form.year" :min="1900" :max="2100" controls-position="right" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.abstract" type="textarea" :rows="3" placeholder="请输入摘要" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

/** 文献 */
interface Reference {
  id: number
  paper_id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number
  volume?: string
  issue?: string
  pages?: string
  doi?: string
  url?: string
  abstract?: string
  vector_id?: string
}

const props = defineProps<{
  references: Reference[]
  loading?: boolean
  paperId?: number
}>()

const emit = defineEmits<{
  (e: 'remove', id: number): void
  (e: 'refresh'): void
}>()

const dialogVisible = ref(false)
const submitting = ref(false)

const form = reactive({
  title: '',
  authors: '',
  journal: '',
  year: new Date().getFullYear(),
  abstract: ''
})

/** 删除文献 */
function handleRemove(id: number) {
  emit('remove', id)
}

/** 手动新增文献 */
async function handleCreate() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写文献标题')
    return
  }
  submitting.value = true
  try {
    await request.post('/references/', {
      title: form.title,
      authors: form.authors,
      journal: form.journal,
      year: form.year,
      abstract: form.abstract,
      paper_id: props.paperId || undefined
    })
    ElMessage.success('文献添加成功')
    dialogVisible.value = false
    form.title = ''
    form.authors = ''
    form.journal = ''
    form.abstract = ''
    emit('refresh')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.reference-list {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);

  .header-title {
    font-weight: 600;
    font-size: 14px;
  }
}

.ref-table {
  width: 100%;

  :deep(.el-table__empty-text) {
    color: var(--text-secondary);
    font-size: 13px;
  }
}

.cell-ellipsis {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>