import request from './request'

/** 版本类型：手动 / 自动 / 回滚 / 回滚前备份 */
export type VersionType = 'manual' | 'auto' | 'rollback' | 'backup'

/** 版本摘要 */
export interface VersionSummary {
  id: number
  paper_id: number
  /** 版本号，从 1 递增 */
  version_number: number
  version_type: VersionType
  /** 版本说明 */
  description: string
  /** 触发节点，如 outline / section / references / polish / quality_check / rollback */
  trigger_node?: string | null
  word_count: number
  chapter_count: number
  reference_count: number
  /** ISO 时间字符串 */
  created_at: string
}

/** 快照中的章节 */
export interface VersionSnapshotChapter {
  title: string
  content: string
  order_index: number
  word_count: number
  summary: string
}

/** 快照中的文献 */
export interface VersionSnapshotReference {
  id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number
}

/** 快照中的论文信息 */
export interface VersionSnapshotPaper {
  title: string
  topic: string
  keywords: string
  abstract: string
  status: string
  /** 大纲（JSON 字符串，需容错解析） */
  outline: string
  content: string
  paper_type: string
  word_limit: number
}

/** 全量快照 */
export interface VersionSnapshot {
  format_version: number
  created_at: string
  paper: VersionSnapshotPaper
  chapters: VersionSnapshotChapter[]
  references: VersionSnapshotReference[]
  workflow?: { last_node?: string; note?: string } | null
}

/** 版本详情（含全量快照） */
export interface VersionDetail extends VersionSummary {
  snapshot: VersionSnapshot
}

/** 回滚结果 */
export interface RollbackResult {
  message: string
  paper_id: number
  /** 回滚到的版本号 */
  target_version_number: number
  /** 回滚前自动备份生成的新版本号 */
  backup_version_number: number
  /** 回滚动作生成的新版本号 */
  rollback_version_number: number
  restored: { chapter_count: number; reference_count: number; word_count: number }
}

/** 差异片段 */
export interface DiffSegment {
  type: 'equal' | 'insert' | 'delete'
  text: string
}

/** 差异项（章节 / 文献 / 大纲小节） */
export interface DiffItem {
  key: string
  /** 差异项名称（章节名 / 文献名 / 大纲小节名） */
  title: string
  status: 'added' | 'removed' | 'modified' | 'unchanged'
  old_title?: string | null
  word_count_old?: number | null
  word_count_new?: number | null
  /** 行级差异片段 */
  segments: DiffSegment[]
  /** true 表示差异过长已截断 */
  truncated: boolean
}

/** 差异维度 */
export interface DiffDimension {
  key: 'title' | 'abstract' | 'keywords' | 'outline' | 'chapters' | 'references'
  /** 维度名称，如「论文标题」 */
  label: string
  status: 'added' | 'removed' | 'modified' | 'unchanged'
  old_value?: string | null
  new_value?: string | null
  /** 用于 title / abstract / keywords 的行内差异 */
  segments: DiffSegment[]
  /** 用于 outline / chapters / references */
  items: DiffItem[]
}

/** 比较的一侧 */
export interface DiffSide {
  /** 与当前内容对比时，后端返回 0 表示当前内容 */
  version_number: number
  /** 例如「v3」或「当前内容」 */
  label: string
  version_type?: string | null
  description?: string | null
  created_at?: string | null
}

/** 版本差异 */
export interface VersionDiff {
  paper_id: number
  /** 左侧 = 请求的那个版本 */
  left: DiffSide
  /** 右侧 = 当前内容 或 目标历史版本 */
  right: DiffSide
  summary: { added: number; removed: number; modified: number; unchanged: number }
  dimensions: DiffDimension[]
}

/** 获取版本列表（按版本号倒序） */
export function getVersions(paperId: number) {
  return request.get<any, VersionSummary[]>(`/papers/${paperId}/versions`)
}

/** 手动保存版本 */
export function createVersion(paperId: number, description: string) {
  return request.post<any, VersionSummary>(`/papers/${paperId}/versions`, { description })
}

/** 获取版本详情（含全量快照） */
export function getVersionDetail(paperId: number, versionId: number) {
  return request.get<any, VersionDetail>(`/papers/${paperId}/versions/${versionId}`)
}

/** 回滚到指定版本（会生成新版本，历史版本不会删除） */
export function rollbackVersion(paperId: number, versionId: number) {
  return request.post<any, RollbackResult>(`/papers/${paperId}/versions/${versionId}/rollback`)
}

/**
 * 版本差异对比
 * 不传 targetVersionId 表示「该版本 vs 当前内容」；传了表示「两个历史版本对比」
 */
export function diffVersion(paperId: number, versionId: number, targetVersionId?: number) {
  const params: Record<string, number> = {}
  if (targetVersionId !== undefined && targetVersionId !== null) {
    params.target_version_id = targetVersionId
  }
  return request.get<any, VersionDiff>(`/papers/${paperId}/versions/${versionId}/diff`, { params })
}