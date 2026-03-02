import { describe, expect, it } from 'vitest'
import { validateDemand } from '../services/demandValidationService'

describe('validateDemand', () => {
  it('valida datas obrigatórias e ordem de datas', () => {
    const result = validateDemand({
      description: 'x',
      project: 'y',
      createdAt: '2026-01-10',
      dueDate: '2026-01-09'
    })

    expect(result.valid).toBe(false)
    expect(result.messages).toContain('Prazo não pode ser anterior à data de registro.')
  })
})
