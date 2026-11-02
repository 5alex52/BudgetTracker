/** Метки записей. */
import { request } from './client'
import type { TagCreate, TagDto, TagUpdate } from './types'

export function listTags(): Promise<TagDto[]> {
  return request<TagDto[]>('/finance/tags/')
}

export function createTag(payload: TagCreate): Promise<TagDto> {
  return request<TagDto>('/finance/tags/', { method: 'POST', body: payload })
}

export function updateTag(tagId: number, payload: TagUpdate): Promise<TagDto> {
  return request<TagDto>(`/finance/tags/${tagId}`, { method: 'PATCH', body: payload })
}

export function deleteTag(tagId: number): Promise<void> {
  return request<void>(`/finance/tags/${tagId}`, { method: 'DELETE' })
}
