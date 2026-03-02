import { describe, expect, it } from 'vitest'
import { exportDemands, importDemands, listDemands, saveDemand } from '../db/demandRepository'

const sample = {
  id: '1',
  description: 'D',
  project: 'P',
  status: 'Não iniciada' as const,
  priority: 'Alta' as const,
  isUrgent: false,
  createdAt: '2026-01-01',
  dueDate: '2026-01-05'
}

describe('demandRepository', () => {
  it('persiste e reabre dados no IndexedDB', async () => {
    await saveDemand(sample)
    const rows = await listDemands()
    expect(rows.some((r) => r.id === sample.id)).toBe(true)
  })

  it('exporta/importa JSON', async () => {
    const exported = await exportDemands()
    await importDemands(exported)
    const rows = await listDemands()
    expect(rows.length).toBeGreaterThan(0)
  })
})
