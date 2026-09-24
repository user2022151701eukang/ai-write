import request, { API_BASE, getToken } from './request'

/** 论文状态 */
export type PaperStatus = 'draft' | 'outline' | 'writing' | 'review' | 'completed'

/** 论文 */
export interface Paper {
  id: number
  title: string
  topic: string
  keywords: string
  abstract: string
  status: PaperStatus
  /** 大纲（JSON 文本） */
  outline: string
  /** 全文（Markdown 文本） */
  content: string
  paper_type: string
  word_limit: number
  author_id: number
  created_at: string
  updated_at: string
}

/** 论文详情中的章节摘要 */
export interface PaperChapterBrief {
  id: number
  title: string
  order_index: number
}

/** 论文详情中的文献摘要 */
export interface PaperReferenceBrief {
  id: number
  title: string
  authors: string
  year: number
}

/** 论文详情 */
export interface PaperDetail extends Paper {
  chapters: PaperChapterBrief[]
  references: PaperReferenceBrief[]
}

/** 创建论文参数 */
export interface PaperCreateData {
  title: string
  topic: string
  keywords: string
  paper_type?: string
  word_limit?: number
}

/** 更新论文参数 */
export interface PaperUpdateData {
  title?: string
  topic?: string
  keywords?: string
  abstract?: string
  outline?: string
  content?: string
  status?: PaperStatus
  word_limit?: number
  paper_type?: string
}

/** 论文列表查询参数 */
export interface PaperListParams {
  skip?: number
  limit?: number
  status?: string
}

/** 大纲章节结构 */
export interface OutlineSection {
  title: string
  points: string[]
  word_count: number
}

/** 大纲结构 */
export interface Outline {
  title: string
  sections: OutlineSection[]
}

/** 生成类接口的通用参数 */
export interface GenerateOptions {
  paper_type?: string
  word_limit?: number
  is_topic_clear?: boolean
  topic?: string
  polish?: boolean
}

/** 选题推荐参数 */
export interface TopicRecommendData {
  field: string
  keywords: string
  requirements: string
}

/** 获取论文列表 */
export function getPaperList(params?: PaperListParams) {
  return request.get<any, Paper[]>('/papers/', { params })
}

/** 获取论文详情 */
export function getPaper(id: number) {
  return request.get<any, PaperDetail>(`/papers/${id}`)
}

/** 创建论文 */
export function createPaper(data: PaperCreateData) {
  return request.post<any, Paper>(`/papers/`, data)
}

/** 更新论文 */
export function updatePaper(id: number, data: PaperUpdateData) {
  return request.put<any, Paper>(`/papers/${id}`, data)
}

/** 删除论文 */
export function deletePaper(id: number) {
  return request.delete<any, void>(`/papers/${id}`)
}

/** 一键生成论文（同步接口） */
export function generatePaper(id: number, options?: GenerateOptions) {
  return request.post<any, Record<string, any>>(`/papers/${id}/generate`, options || {})
}

/** 生成大纲 */
export function generateOutline(id: number, options?: GenerateOptions) {
  return request.post<any, { paper_id: number; outline: Outline }>(`/papers/${id}/outline`, options || {})
}

/** 选题推荐 */
export function recommendTopics(id: number, data: TopicRecommendData) {
  return request.post<any, { paper_id: number; topics: string }>(`/papers/${id}/topics`, data)
}

/**
 * 生成流式接口地址（EventSource 无法携带 Authorization 头，因此通过 URL 传 token）
 */
export function getStreamGenerateUrl(id: number) {
  const token = encodeURIComponent(getToken())
  return `${API_BASE}/papers/${id}/stream-generate?token=${token}`
}

/** 导出格式 */
export type ExportFormat = 'docx' | 'pdf' | 'md'

/** 导出论文文件（docx / pdf / md），返回二进制内容 */
export function exportPaperFile(id: number, format: ExportFormat) {
  return request.get<any, Blob>(`/papers/${id}/export`, {
    params: { format },
    responseType: 'blob'
  })
}