/** Templates for quick record entry. */
import { request } from './client'
import type { TemplateCreate, TemplateDto, TemplateUpdate, TransactionDto } from './types'

export function listTemplates(): Promise<TemplateDto[]> {
  return request<TemplateDto[]>('/finance/templates/')
}

export function createTemplate(payload: TemplateCreate): Promise<TemplateDto> {
  return request<TemplateDto>('/finance/templates/', { method: 'POST', body: payload })
}

export function updateTemplate(templateId: number, payload: TemplateUpdate): Promise<TemplateDto> {
  return request<TemplateDto>(`/finance/templates/${templateId}`, { method: 'PATCH', body: payload })
}

export function deleteTemplate(templateId: number): Promise<void> {
  return request<void>(`/finance/templates/${templateId}`, { method: 'DELETE' })
}

/** Create a record from a template: rules and balance are computed by the backend. */
export function applyTemplate(templateId: number, date?: string): Promise<TransactionDto> {
  return request<TransactionDto>(`/finance/templates/${templateId}/apply`, { method: 'POST', query: { date } })
}
