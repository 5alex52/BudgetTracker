/** Правила авто-категоризации. */
import { request } from './client'
import type { RuleApplyResultDto, RuleCreate, RuleDto, RuleUpdate } from './types'

export function listRules(): Promise<RuleDto[]> {
  return request<RuleDto[]>('/finance/rules/')
}

export function createRule(payload: RuleCreate): Promise<RuleDto> {
  return request<RuleDto>('/finance/rules/', { method: 'POST', body: payload })
}

export function updateRule(ruleId: number, payload: RuleUpdate): Promise<RuleDto> {
  return request<RuleDto>(`/finance/rules/${ruleId}`, { method: 'PATCH', body: payload })
}

export function deleteRule(ruleId: number): Promise<void> {
  return request<void>(`/finance/rules/${ruleId}`, { method: 'DELETE' })
}

/** Прогон правил по существующим записям; `dryRun` только считает совпадения. */
export function applyRules(params: {
  startDate?: string
  endDate?: string
  dryRun?: boolean
} = {}): Promise<RuleApplyResultDto> {
  return request<RuleApplyResultDto>('/finance/rules/apply', {
    method: 'POST',
    query: { start_date: params.startDate, end_date: params.endDate, dry_run: params.dryRun ?? false },
  })
}
