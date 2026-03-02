import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { App } from '../App'

describe('App', () => {
  it('executa fluxo básico de criar demanda', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('E-mail'), 'user@webdemands.com')
    await user.type(screen.getByLabelText('Senha'), '123456')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    await user.click(screen.getByRole('button', { name: 'Nova demanda' }))
    await user.type(screen.getByLabelText('Descrição'), 'Nova demanda')
    await user.type(screen.getByLabelText('Projeto'), 'Web')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))
    await user.click(screen.getByRole('button', { name: 'Consultar demandas' }))

    expect(await screen.findByText(/Nova demanda/)).toBeInTheDocument()
  })
})
