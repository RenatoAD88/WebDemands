export type DemandStatus = 'Não iniciada' | 'Em andamento' | 'Bloqueado' | 'Requer revisão' | 'Cancelado' | 'Concluído'
export type DemandPriority = 'Alta' | 'Média' | 'Baixa'

export interface Demand {
  id: string
  description: string
  project: string
  status: DemandStatus
  priority: DemandPriority
  isUrgent: boolean
  createdAt: string
  dueDate: string
  completedAt?: string
}

export type DemandSituation = 'Dentro do Prazo' | 'Em Atraso' | 'Concluída no Prazo' | 'Concluída em Atraso'
