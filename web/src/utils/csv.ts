import type { Demand } from '../types/demand'

export function demandsToCsv(items: Demand[]): string {
  const header = 'id,description,project,status,priority,isUrgent,createdAt,dueDate,completedAt'
  const rows = items.map((d) => [d.id, d.description, d.project, d.status, d.priority, d.isUrgent, d.createdAt, d.dueDate, d.completedAt ?? ''].join(','))
  return [header, ...rows].join('\n')
}
