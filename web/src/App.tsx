import { useEffect, useMemo, useState } from 'react'
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

type UserRole = 'usuario' | 'admin'
type Screen = 'inicio' | 'nova-demanda' | 'consultar-demandas' | 'importar-exportar'

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function onSubmit(event: React.FormEvent) {
    event.preventDefault()

    if (!email.trim() || !password.trim()) {
      setError('Informe e-mail e senha para continuar.')
      return
    }

    setError('')
    onLogin()
  }

  return (
    <section>
      <h1>WebDemands</h1>
      <h2>Login</h2>
      <form onSubmit={onSubmit}>
        <input aria-label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input aria-label="Senha" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit">Entrar</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function AccessGate({ allowedRoles, userRole, children }: { allowedRoles: UserRole[]; userRole: UserRole; children: JSX.Element }) {
  if (!allowedRoles.includes(userRole)) {
    return <p>Você não possui acesso a esta tela.</p>
  }

  return children
}

function HomePage() {
  return (
    <section>
      <h2>Acesso às telas</h2>
      <p>Use o menu para navegar entre todas as telas disponíveis para o perfil de usuário.</p>
    </section>
  )
}

function NewDemandPage({ onCreated }: { onCreated: () => Promise<void> }) {
  const [form, setForm] = useState(defaultForm)
  const [error, setError] = useState('')

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
    await onCreated()
  }

  return (
    <section>
      <h2>Nova demanda</h2>
      <form onSubmit={onSubmit}>
        <input aria-label="Descrição" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input aria-label="Projeto" value={form.project} onChange={(e) => setForm({ ...form, project: e.target.value })} />
        <input aria-label="Data de registro" type="date" value={form.createdAt} onChange={(e) => setForm({ ...form, createdAt: e.target.value })} />
        <input aria-label="Prazo" type="date" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} />
        <button type="submit">Salvar</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function DemandsPage({ demands, onDelete }: { demands: Demand[]; onDelete: (id: string) => Promise<void> }) {
  return (
    <section>
      <h2>Consultar demandas</h2>
      <ul>
        {demands.map((d) => (
          <li key={d.id}>
            {d.description} - {calculateSituation(d)}
            <button onClick={() => onDelete(d.id)}>Excluir</button>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ImportExportPage({ onImported }: { onImported: () => Promise<void> }) {
  async function onExport() {
    const json = await exportDemands()
    await navigator.clipboard?.writeText(json)
  }

  async function onImport() {
    const raw = window.prompt('Cole o JSON exportado')
    if (!raw) return
    await importDemands(raw)
    await onImported()
  }

  return (
    <section>
      <h2>Importação e exportação</h2>
      <button onClick={onExport}>Exportar JSON</button>
      <button onClick={onImport}>Importar JSON</button>
    </section>
  )
}

export function App() {
  const [demands, setDemands] = useState<Demand[]>([])
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentScreen, setCurrentScreen] = useState<Screen>('inicio')
  const userRole: UserRole = 'usuario'

  const screensForUser = useMemo(
    () => [
      { key: 'inicio' as Screen, label: 'Início' },
      { key: 'nova-demanda' as Screen, label: 'Nova demanda' },
      { key: 'consultar-demandas' as Screen, label: 'Consultar demandas' },
      { key: 'importar-exportar' as Screen, label: 'Importar/Exportar' }
    ],
    []
  )

  async function refresh() {
    setDemands(await listDemands())
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function onDelete(id: string) {
    await deleteDemand(id)
    await refresh()
  }

  const screenContent: Record<Screen, JSX.Element> = {
    inicio: <HomePage />,
    'nova-demanda': <NewDemandPage onCreated={refresh} />,
    'consultar-demandas': <DemandsPage demands={demands} onDelete={onDelete} />,
    'importar-exportar': <ImportExportPage onImported={refresh} />
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <main>
      <h1>WebDemands</h1>
      <p>Perfil ativo: usuário</p>
      <nav aria-label="Navegação principal">
        {screensForUser.map((screen) => (
          <button key={screen.key} onClick={() => setCurrentScreen(screen.key)} style={{ marginRight: 12 }}>
            {screen.label}
          </button>
        ))}
      </nav>

      <AccessGate allowedRoles={['usuario', 'admin']} userRole={userRole}>
        {screenContent[currentScreen]}
      </AccessGate>
    </main>
  )
}
