<template>
  <div class="page-container">
    <div class="create-card app-card app-card--lg">
      <h2 class="card-title">创建新论文</h2>
      <p class="card-subtitle">填写基本信息，系统将据此生成大纲与全文</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="论文标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入论文标题（至少 5 个字符）" />
        </el-form-item>
        <el-form-item label="选题方向" prop="topic">
          <el-input v-model="form.topic" placeholder="如：基于多 Agent 协作的学术论文自动写作研究" />
        </el-form-item>
        <el-form-item label="关键词" prop="keywords">
          <el-input v-model="form.keywords" placeholder="多个关键词用逗号分隔，如：大模型,多智能体,RAG" />
        </el-form-item>
        <el-form-item label="论文类型" prop="paper_type">
          <el-select v-model="form.paper_type" placeholder="请选择论文类型" style="width: 100%">
            <el-option label="研究论文" value="research" />
            <el-option label="综述论文" value="review" />
            <el-option label="应用研究" value="application" />
            <el-option label="学位论文" value="thesis" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标字数" prop="word_limit">
          <el-input-number
            v-model="form.word_limit"
            :min="1000"
            :max="100000"
            :step="1000"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleCreate">创建并进入工作台</el-button>
          <el-button @click="router.back()">返回</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { usePaperStore } from '@/stores/paper'

const router = useRouter()
const paperStore = usePaperStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  title: '',
  topic: '',
  keywords: '',
  paper_type: 'research',
  word_limit: 10000
})

const rules: FormRules = {
  title: [
    { required: true, message: '请输入论文标题', trigger: 'blur' },
    { min: 5, message: '论文标题至少 5 个字符', trigger: 'blur' }
  ],
  topic: [{ required: true, message: '请输入选题方向', trigger: 'blur' }]
}

/** 创建论文并跳转工作台 */
async function handleCreate() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const paper = await paperStore.createPaper({
        title: form.title,
        topic: form.topic,
        keywords: form.keywords,
        paper_type: form.paper_type,
        word_limit: form.word_limit
      })
      ElMessage.success('论文创建成功')
      router.push(`/papers/${paper.id}/edit`)
    } catch (e) {
      // 错误已由拦截器统一提示
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.create-card {
  max-width: 680px;
  margin: 0 auto;
  padding: 28px 30px;
}

.card-title {
  font-size: 20px;
  font-weight: 700;
}

.card-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 6px 0 22px;
}
</style>