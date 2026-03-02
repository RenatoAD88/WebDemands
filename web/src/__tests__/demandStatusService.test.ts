import { describe, expect, it } from 'vitest'
import { calculateSituation } from '../services/demandStatusService'

describe('calculateSituation', () => {
  it('marca demanda pendente vencida como em atraso', () => {
    expect(
      calculateSituation({
        id: '1',
        description: 'A',
        project: 'P',
        status: 'Em andamento',
        priority: 'Média',
        isUrgent: false,
        createdAt: '2026-01-01',
        dueDate: '2026-01-02'
      }, new Date('2026-01-03'))
    ).toBe('Em Atraso')
  })
})
