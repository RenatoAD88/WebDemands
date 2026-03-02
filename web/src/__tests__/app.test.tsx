import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { App } from '../App'

describe('App', () => {
  it('executa fluxo básico de criar demanda', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('Descrição'), 'Nova demanda')
    await user.type(screen.getByLabelText('Projeto'), 'Web')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText(/Nova demanda/)).toBeInTheDocument()
  })
})
