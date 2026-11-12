/** Categories: tree, flat list, counters and CRUD. */
import { request } from './client'
import type { CategoryCreate, CategoryDto, CategoryNodeDto, CategoryStatDto, CategoryUpdate } from './types'

export function listCategories(params?: { type?: 'income' | 'expense' | 'transfer'; parentId?: number }): Promise<
  CategoryDto[]
> {
  return request<CategoryDto[]>('/finance/categories/', {
    query: { category_type: params?.type, parent_id: params?.parentId, limit: 500 },
  })
}

export function getCategoryTree(params?: {
  type?: 'income' | 'expense' | 'transfer'
  startDate?: string
  endDate?: string
}): Promise<CategoryNodeDto[]> {
  return request<CategoryNodeDto[]>('/finance/categories/tree', {
    query: { category_type: params?.type, start_date: params?.startDate, end_date: params?.endDate },
  })
}

export function getCategoryStats(params?: {
  type?: 'income' | 'expense' | 'transfer'
  startDate?: string
  endDate?: string
}): Promise<CategoryStatDto[]> {
  return request<CategoryStatDto[]>('/finance/categories/stats', {
    query: { category_type: params?.type, start_date: params?.startDate, end_date: params?.endDate },
  })
}

export function createCategory(payload: CategoryCreate): Promise<CategoryDto> {
  return request<CategoryDto>('/finance/categories/', { method: 'POST', body: payload })
}

export function updateCategory(categoryId: number, payload: CategoryUpdate): Promise<CategoryDto> {
  return request<CategoryDto>(`/finance/categories/${categoryId}`, { method: 'PATCH', body: payload })
}

export function deleteCategory(categoryId: number): Promise<void> {
  return request<void>(`/finance/categories/${categoryId}`, { method: 'DELETE' })
}
