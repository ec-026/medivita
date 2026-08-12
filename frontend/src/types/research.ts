export type ResearchStage =
  | 'safety'
  | 'planning'
  | 'search'
  | 'page_retrieval'
  | 'evidence'
  | 'research_decision'
  | 'generation'
  | 'citation'
  | 'complete'

export type ResearchStatus = 'pending' | 'running' | 'completed' | 'warning' | 'failed'

export interface ResearchTraceEvent {
  id: string
  stage: ResearchStage
  status: ResearchStatus
  label: string
  tool?: string
  round?: number
  source_id?: string
  source_name?: string
  backend?: string
  query?: string
  result_count?: number
  page_count?: number
  evidence_count?: number
  citation_count?: number
  model?: string
  provider?: string
  retrieval_type?: string
  elapsed_ms?: number
  message?: string
}

export interface ResearchSummary {
  rounds: number
  evidence_count: number
  citation_count: number
  total_ms: number
}
