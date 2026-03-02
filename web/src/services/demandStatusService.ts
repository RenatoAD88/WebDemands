import type { Demand, DemandSituation } from '../types/demand'

export function calculateSituation(demand: Demand, today = new Date()): DemandSituation {
  const due = new Date(demand.dueDate)
  if (demand.status === 'Concluído') {
    const completed = demand.completedAt ? new Date(demand.completedAt) : today
    return completed <= due ? 'Concluída no Prazo' : 'Concluída em Atraso'
  }
  return today <= due ? 'Dentro do Prazo' : 'Em Atraso'
}
