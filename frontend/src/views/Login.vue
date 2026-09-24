<template>
  <div class="login-page">
    <div class="login-card">
      <div class="card-title">📝 AI 论文写作系统</div>
      <div class="card-subtitle">登录后开始你的论文写作之旅</div>

      <el-form :model="form" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>

      <div class="register-tip">
        <span>还没有账号？</span>
        <a class="register-link" @click="openRegister">立即注册</a>
      </div>
    </div>

    <!-- 注册弹窗 -->
    <el-dialog v-model="dialogVisible" title="注册账号" width="420px">
      <el-form ref="registerFormRef" :model="registerForm" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" placeholder="至少 3 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="registering" @click="handleRegister">注册并登录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const registering = ref(false)
const dialogVisible = ref(false)
const registerFormRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

/** 登录 */
async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    // 错误已由拦截器统一提示
  } finally {
    loading.value = false
  }
}

/** 打开注册弹窗 */
function openRegister() {
  dialogVisible.value = true
}

/** 注册并自动登录 */
async function handleRegister() {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    registering.value = true
    try {
      await userStore.register({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password
      })
      ElMessage.success('注册成功，已自动登录')
      dialogVisible.value = false
      router.push('/')
    } catch (e) {
      // 错误已由拦截器统一提示
    } finally {
      registering.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-gradient);
  border-radius: 16px;
  padding: 40px 20px;
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(31, 41, 55, 0.18);
  padding: 32px 30px;
}

.card-title {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 6px;
}

.card-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  background: var(--primary-gradient);
  border: none;
  font-weight: 600;
}

.register-tip {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.register-link {
  color: var(--primary-color);
  cursor: pointer;
  font-weight: 600;
  margin-left: 4px;
}
</style>