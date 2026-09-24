import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  createPaper as createPaperApi,
  deletePaper as deletePaperApi,
  generateOutline as generateOutlineApi,
  generatePaper as generatePaperApi,
  getPaper,
  getPaperList,
  recommendTopics as recommendTopicsApi,
  updatePaper as updatePaperApi
} from '@/api/paper'
import type {
  GenerateOptions,
  Paper,
  PaperCreateData,
  PaperDetail,
  PaperListParams,
  PaperUpdateData,
  TopicRecommendData
} from '@/api/paper'

/** 论文状态管理 */
export const usePaperStore = defineStore('paper', () => {
  const papers = ref<Paper[]>([])
  const currentPaper = ref<PaperDetail | null>(null)
  const loading = ref(false)
  const generating = ref(false)

  /** 论文总数 */
  const paperCount = computed(() => papers.value.length)
  /** 草稿数量 */
  const draftCount = computed(() => papers.value.filter((p) => p.status === 'draft').length)
  /** 已完成数量 */
  const completedCount = computed(() => papers.value.filter((p) => p.status === 'completed').length)

  /** 获取论文列表 */
  async function fetchPapers(params?: PaperListParams) {
    loading.value = true
    try {
      papers.value = await getPaperList(params)
      return papers.value
    } finally {
      loading.value = false
    }
  }

  /** 获取论文详情 */
  async function fetchPaper(id: number) {
    loading.value = true
    try {
      currentPaper.value = await getPaper(id)
      return currentPaper.value
    } finally {
      loading.value = false
    }
  }

  /** 创建论文 */
  async function createPaper(data: PaperCreateData) {
    const paper = await createPaperApi(data)
    papers.value = [paper, ...papers.value]
    return paper
  }

  /** 更新论文 */
  async function updatePaper(id: number, data: PaperUpdateData) {
    const paper = await updatePaperApi(id, data)
    const index = papers.value.findIndex((p) => p.id === id)
    if (index > -1) papers.value[index] = { ...papers.value[index], ...paper }
    if (currentPaper.value?.id === id) currentPaper.value = { ...currentPaper.value, ...paper }
    return paper
  }

  /** 删除论文 */
  async function deletePaper(id: number) {
    await deletePaperApi(id)
    papers.value = papers.value.filter((p) => p.id !== id)
    if (currentPaper.value?.id === id) currentPaper.value = null
  }

  /** 一键生成论文 */
  async function generatePaper(id: number, options?: GenerateOptions) {
    generating.value = true
    try {
      return await generatePaperApi(id, options)
    } finally {
      generating.value = false
    }
  }

  /** 生成大纲 */
  async function generateOutline(id: number, options?: GenerateOptions) {
    generating.value = true
    try {
      return await generateOutlineApi(id, options)
    } finally {
      generating.value = false
    }
  }

  /** 选题推荐 */
  async function recommendTopics(id: number, data: TopicRecommendData) {
    generating.value = true
    try {
      return await recommendTopicsApi(id, data)
    } finally {
      generating.value = false
    }
  }

  return {
    papers,
    currentPaper,
    loading,
    generating,
    paperCount,
    draftCount,
    completedCount,
    fetchPapers,
    fetchPaper,
    createPaper,
    updatePaper,
    deletePaper,
    generatePaper,
    generateOutline,
    recommendTopics
  }
})