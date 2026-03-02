import { useEffect, useState } from 'react'
import type { Demand } from './types/demand'
import { calculateSituation } from './services/demandStatusService'
import { validateDemand } from './services/demandValidationService'
import { deleteDemand, exportDemands, importDemands, listDemands, saveDemand } from './db/demandRepository'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const defaultForm: Omit<Demand, 'id'> = {
  description: '',
  project: '',
  status: 'Não iniciada',
  priority: 'Média',
  isUrgent: false,
  createdAt: todayIso(),
  dueDate: todayIso()
}

export function App() {
  const [demands, setDemands] = useState<Demand[]>([])
  const [form, setForm] = useState(defaultForm)
  const [error, setError] = useState('')

  async function refresh() {
    setDemands(await listDemands())
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const result = validateDemand(form)
    if (!result.valid) {
      setError(result.messages.join(' '))
      return
    }

    setError('')
    await saveDemand({ ...form, id: crypto.randomUUID() })
    setForm(defaultForm)
    await refresh()
  }

  async function onDelete(id: string) {
    await deleteDemand(id)
    await refresh()
  }

  async function onExport() {
    const json = await exportDemands()
    navigator.clipboard?.writeText(json)
  }

  async function onImport() {
    const raw = window.prompt('Cole o JSON exportado')
    if (!raw) return
    await importDemands(raw)
    await refresh()
  }

  return (
    <main>
      <h1>WebDemands</h1>
      <button onClick={onExport}>Exportar JSON</button>
      <button onClick={onImport}>Importar JSON</button>
      <form onSubmit={onSubmit}>
        <input aria-label="Descrição" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input aria-label="Projeto" value={form.project} onChange={(e) => setForm({ ...form, project: e.target.value })} />
        <input aria-label="Data de registro" type="date" value={form.createdAt} onChange={(e) => setForm({ ...form, createdAt: e.target.value })} />
        <input aria-label="Prazo" type="date" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} />
        <button type="submit">Salvar</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <ul>
        {demands.map((d) => (
          <li key={d.id}>
            {d.description} - {calculateSituation(d)}
            <button onClick={() => onDelete(d.id)}>Excluir</button>
          </li>
        ))}
      </ul>
    </main>
  )
}
