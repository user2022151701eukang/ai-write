import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createChapter as createChapterApi,
  deleteChapter as deleteChapterApi,
  generateChapter as generateChapterApi,
  getChaptersByPaper,
  polishChapter as polishChapterApi,
  updateChapter as updateChapterApi
} from '@/api/chapter'
import type { Chapter, ChapterGenerateOptions, PolishFocus } from '@/api/chapter'
import {
  generateOutline as generateOutlineApi,
  getPaper,
  getStreamGenerateUrl,
  updatePaper as updatePaperApi
} from '@/api/paper'
import type { GenerateOptions, PaperDetail, PaperUpdateData } from '@/api/paper'
import { getToken } from '@/api/request'

/** 日志条目 */
export interface EditorLog {
  time: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

/** SSE 事件结构 */
interface StreamEventPayload {
  event: string
  step?: string
  message?: string
  progress?: number
  scope?: string
  title?: string
  content?: string
  index?: number
  total?: number
  word_count?: number
  outline?: any
  references?: any[]
  paper_id?: number
  chapters?: any[]
  reference_count?: number
}

/** 当前时间字符串 */
function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

/** 编辑器（论文工作台）状态管理 */
export const useEditorStore = defineStore('editor', () => {
  const paper = ref<PaperDetail | null>(null)
  const chapters = ref<Chapter[]>([])
  const currentChapter = ref<Chapter | null>(null)
  const streamingText = ref('')
  const streamingSection = ref('')
  const topicsText = ref('')
  const progress = ref(0)
  const statusText = ref('')
  const logs = ref<EditorLog[]>([])
  const generating = ref(false)
  const saving = ref(false)

  let controller: AbortController | null = null

  /** 追加日志 */
  function pushLog(message: string, type: EditorLog['type'] = 'info') {
    logs.value.push({ time: now(), message, type })
    if (logs.value.length > 200) logs.value.shift()
  }

  /** 同时拉取论文详情与章节列表 */
  async function fetchPaperAndChapters(paperId: number) {
    const [detail, chapterList] = await Promise.all([
      getPaper(paperId),
      getChaptersByPaper(paperId)
    ])
    paper.value = detail
    chapters.value = chapterList
    if (currentChapter.value) {
      const matched = chapterList.find((c) => c.id === currentChapter.value?.id)
      currentChapter.value = matched || null
    }
    return detail
  }

  /** 设置当前编辑章节 */
  function setCurrentChapter(chapter: Chapter | null) {
    currentChapter.value = chapter
  }

  /** 保存章节 */
  async function saveChapter(chapter: Chapter, content: string) {
    saving.value = true
    try {
      const updated = await updateChapterApi(chapter.id, { title: chapter.title, content })
      const index = chapters.value.findIndex((c) => c.id === chapter.id)
      if (index > -1) chapters.value[index] = updated
      currentChapter.value = updated
      ElMessage.success('章节已保存')
      return updated
    } finally {
      saving.value = false
    }
  }

  /** AI 撰写章节 */
  async function generateChapter(chapterId: number, options?: ChapterGenerateOptions) {
    generating.value = true
    statusText.value = '正在撰写章节…'
    try {
      const updated = await generateChapterApi(chapterId, options)
      const index = chapters.value.findIndex((c) => c.id === chapterId)
      if (index > -1) chapters.value[index] = updated
      if (currentChapter.value?.id === chapterId) currentChapter.value = updated
      pushLog(`章节「${updated.title}」撰写完成`, 'success')
      return updated
    } finally {
      generating.value = false
      statusText.value = ''
    }
  }

  /** AI 润色章节 */
  async function polishChapter(chapterId: number, focus: PolishFocus) {
    generating.value = true
    statusText.value = '正在润色章节…'
    try {
      const updated = await polishChapterApi(chapterId, focus)
      const index = chapters.value.findIndex((c) => c.id === chapterId)
      if (index > -1) chapters.value[index] = updated
      if (currentChapter.value?.id === chapterId) currentChapter.value = updated
      ElMessage.success('润色完成')
      pushLog(`章节「${updated.title}」润色完成（${focus}）`, 'success')
      return updated
    } finally {
      generating.value = false
      statusText.value = ''
    }
  }

  /** 新增章节 */
  async function addChapter() {
    if (!paper.value) return null
    const chapter = await createChapterApi({
      paper_id: paper.value.id,
      title: `第 ${chapters.value.length + 1} 章`,
      content: '',
      order_index: chapters.value.length
    })
    chapters.value.push(chapter)
    currentChapter.value = chapter
    ElMessage.success('已新增章节')
    return chapter
  }

  /** 删除章节 */
  async function removeChapter(id: number) {
    await deleteChapterApi(id)
    chapters.value = chapters.value.filter((c) => c.id !== id)
    if (currentChapter.value?.id === id) currentChapter.value = null
    ElMessage.success('章节已删除')
  }

  /** 保存大纲（JSON 字符串） */
  async function saveOutline(outlineText: string) {
    if (!paper.value) return
    saving.value = true
    try {
      await updatePaperApi(paper.value.id, { outline: outlineText })
      if (paper.value) paper.value.outline = outlineText
      ElMessage.success('大纲已保存')
    } finally {
      saving.value = false
    }
  }

  /** 生成大纲（同步接口，返回大纲对象） */
  async function generateOutline() {
    if (!paper.value) return null
    generating.value = true
    statusText.value = '正在生成大纲…'
    try {
      const res = await generateOutlineApi(paper.value.id, {
        paper_type: paper.value.paper_type,
        word_limit: paper.value.word_limit,
        topic: paper.value.topic
      })
      const text = JSON.stringify(res.outline, null, 2)
      if (paper.value) paper.value.outline = text
      pushLog('大纲生成完成', 'success')
      return text
    } catch (e: any) {
      pushLog('大纲生成失败', 'error')
      return null
    } finally {
      generating.value = false
      statusText.value = ''
    }
  }

  /** 中断流式生成 */
  function stopStream() {
    if (controller) {
      controller.abort()
      controller = null
    }
    generating.value = false
    statusText.value = '已停止生成'
    pushLog('用户中断了生成', 'warning')
  }

  /** 处理单条 SSE 事件 */
  async function handleEvent(payload: StreamEventPayload, paperId: number) {
    switch (payload.event) {
      case 'status':
        statusText.value = payload.message || ''
        if (typeof payload.progress === 'number') progress.value = payload.progress
        if (payload.message) pushLog(payload.message)
        break
      case 'token':
        if (payload.scope === 'topic') {
          topicsText.value += payload.content || ''
        } else {
          if (payload.title && payload.title !== streamingSection.value) {
            streamingSection.value = payload.title
          }
          streamingText.value += payload.content || ''
        }
        break
      case 'outline':
        if (paper.value && payload.outline) {
          paper.value.outline = JSON.stringify(payload.outline, null, 2)
        }
        if (typeof payload.progress === 'number') progress.value = payload.progress
        pushLog('大纲已生成', 'success')
        break
      case 'references':
        pushLog(`检索到 ${payload.references?.length || 0} 篇相关文献`)
        break
      case 'section_start':
        streamingSection.value = payload.title || ''
        streamingText.value = ''
        if (typeof payload.progress === 'number') progress.value = payload.progress
        statusText.value = `正在撰写：${payload.title || ''}（${payload.index}/${payload.total}）`
        pushLog(`开始撰写章节：${payload.title || ''}`)
        break
      case 'section_done':
        streamingSection.value = payload.title || streamingSection.value
        // 后端章节完成后会回传清理过 AI 附加内容的正文，据此校正流式显示
        if (payload.content) streamingText.value = payload.content
        if (typeof payload.progress === 'number') progress.value = payload.progress
        pushLog(
          `章节「${payload.title || ''}」完成，共 ${payload.word_count || 0} 字`,
          'success'
        )
        break
      case 'polish_done':
        if (paper.value && payload.content) paper.value.content = payload.content
        pushLog('全文润色完成', 'success')
        break
      case 'topics':
        topicsText.value = payload.content || ''
        pushLog('选题推荐生成完成', 'success')
        break
      case 'warning':
        pushLog(payload.message || '警告', 'warning')
        ElMessage.warning(payload.message || '生成过程出现警告')
        break
      case 'error':
        pushLog(payload.message || '生成失败', 'error')
        ElMessage.error(payload.message || '生成失败')
        break
      case 'done':
        if (typeof payload.progress === 'number') progress.value = payload.progress
        statusText.value = '生成完成'
        pushLog('论文生成完成', 'success')
        await fetchPaperAndChapters(paperId)
        break
      default:
        break
    }
  }

  /**
   * 流式生成论文
   * EventSource 无法携带 Authorization 头，因此使用 fetch 读取流并手动解析 SSE
   */
  async function generateStream(paperId: number, options?: GenerateOptions) {
    if (generating.value) {
      ElMessage.warning('正在生成中，请稍候')
      return
    }
    generating.value = true
    progress.value = 0
    streamingText.value = ''
    streamingSection.value = ''
    topicsText.value = ''
    logs.value = []
    statusText.value = '正在连接生成服务…'
    controller = new AbortController()

    const params = new URLSearchParams()
    params.set('polish', options?.polish === false ? 'false' : 'true')
    params.set('is_topic_clear', options?.is_topic_clear === false ? 'false' : 'true')
    if (options?.paper_type) params.set('paper_type', options.paper_type)
    if (options?.word_limit) params.set('word_limit', String(options.word_limit))
    if (options?.topic) params.set('topic', options.topic)
    params.set('token', getToken())

    const url = `${getStreamGenerateUrl(paperId).split('?')[0]}?${params.toString()}`

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${getToken()}`
        },
        signal: controller.signal
      })
      if (!response.ok) {
        throw new Error(`请求失败：${response.status}`)
      }
      if (!response.body) {
        throw new Error('当前浏览器不支持流式读取')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 按空行切分事件
        let boundary = buffer.indexOf('\n\n')
        while (boundary > -1) {
          const rawEvent = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const dataLines = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trim())
          if (dataLines.length) {
            const dataText = dataLines.join('\n')
            if (dataText === '[DONE]') {
              buffer = ''
              break
            }
            try {
              const payload = JSON.parse(dataText) as StreamEventPayload
              await handleEvent(payload, paperId)
            } catch (e) {
              // 忽略无法解析的片段
            }
          }
          boundary = buffer.indexOf('\n\n')
        }
      }
      pushLog('流式连接已结束')
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        pushLog('生成已中断', 'warning')
      } else {
        statusText.value = '生成失败'
        ElMessage.error(e?.message || '生成失败')
        pushLog(e?.message || '生成失败', 'error')
      }
    } finally {
      generating.value = false
      controller = null
    }
  }

  /** 直接更新论文（供页面保存使用） */
  async function updatePaperInfo(id: number, data: PaperUpdateData) {
    const updated = await updatePaperApi(id, data)
    if (paper.value && paper.value.id === id) {
      paper.value = { ...paper.value, ...updated }
    }
    return updated
  }

  return {
    paper,
    chapters,
    currentChapter,
    streamingText,
    streamingSection,
    topicsText,
    progress,
    statusText,
    logs,
    generating,
    saving,
    fetchPaperAndChapters,
    setCurrentChapter,
    saveChapter,
    generateChapter,
    polishChapter,
    addChapter,
    removeChapter,
    saveOutline,
    generateOutline,
    updatePaperInfo,
    generateStream,
    stopStream,
    pushLog
  }
})