import type { Demand } from '../types/demand'

export interface DemandValidationResult {
  valid: boolean
  messages: string[]
}

export function validateDemand(input: Partial<Demand>): DemandValidationResult {
  const messages: string[] = []
  if (!input.description?.trim()) messages.push('Descrição é obrigatória.')
  if (!input.project?.trim()) messages.push('Projeto é obrigatório.')
  if (!input.createdAt) messages.push('Data de registro é obrigatória.')
  if (!input.dueDate) messages.push('Prazo é obrigatório.')

  if (input.createdAt && input.dueDate && new Date(input.dueDate) < new Date(input.createdAt)) {
    messages.push('Prazo não pode ser anterior à data de registro.')
  }

  if (input.completedAt && input.createdAt && new Date(input.completedAt) < new Date(input.createdAt)) {
    messages.push('Data de conclusão não pode ser anterior à data de registro.')
  }

  return { valid: messages.length === 0, messages }
}
