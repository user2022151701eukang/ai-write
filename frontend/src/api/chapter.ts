import request from './request'

/** 章节 */
export interface Chapter {
  id: number
  paper_id: number
  parent_id: number | null
  title: string
  content: string
  summary: string
  order_index: number
  word_count: number
  created_at: string
  updated_at: string
}

/** 创建章节参数 */
export interface ChapterCreateData {
  paper_id: number
  title: string
  content?: string
  summary?: string
  order_index?: number
  parent_id?: number | null
}

/** 更新章节参数 */
export interface ChapterUpdateData {
  title?: string
  content?: string
  summary?: string
  order_index?: number
  parent_id?: number | null
}

/** 章节生成参数 */
export interface ChapterGenerateOptions {
  word_count?: number
  style?: string
  outline_points?: string[]
  use_references?: boolean
}

/** 润色侧重点 */
export type PolishFocus = 'language' | 'logic' | 'format' | 'all'

/** 获取某论文的所有章节 */
export function getChaptersByPaper(paperId: number) {
  return request.get<any, Chapter[]>(`/chapters/paper/${paperId}`)
}

/** 创建章节 */
export function createChapter(data: ChapterCreateData) {
  return request.post<any, Chapter>(`/chapters/`, data)
}

/** 获取章节详情 */
export function getChapter(id: number) {
  return request.get<any, Chapter>(`/chapters/${id}`)
}

/** 更新章节 */
export function updateChapter(id: number, data: ChapterUpdateData) {
  return request.put<any, Chapter>(`/chapters/${id}`, data)
}

/** 删除章节 */
export function deleteChapter(id: number) {
  return request.delete<any, void>(`/chapters/${id}`)
}

/** AI 撰写章节 */
export function generateChapter(id: number, options?: ChapterGenerateOptions) {
  return request.post<any, Chapter>(`/chapters/${id}/generate`, options || {})
}

/** AI 润色章节 */
export function polishChapter(id: number, focus: PolishFocus) {
  return request.post<any, Chapter>(`/chapters/${id}/polish`, { focus })
}