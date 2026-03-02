# DIAGNÓSTICO BASELINE — WebDemands (PR #0)

## 1) Inventário técnico

## Stack detectada (real do repositório atual)
- **Linguagem principal:** Python 3.10
- **UI/Desktop:** PySide6 (Qt)
- **Build desktop:** PyInstaller (`app.spec`, `DemandasApp.spec`, `build_windows.bat`)
- **Testes:** pytest
- **Dependências de IA:** OpenAI SDK, Hugging Face Hub, Requests
- **Banco/persistência:** arquivos locais CSV/JSON e SQLite auxiliares

> **Conclusão:** o repositório atual **não é um projeto web Node/React/Vite**; ele está estruturado como aplicativo desktop Python derivado do MyDemands.

## Tooling e gerenciadores detectados
- **Gerenciador Python:** `pip` via `requirements.txt`
- **Node/npm/ts disponíveis no ambiente:** sim, porém **sem `package.json` no repo**

## Versões detectadas no ambiente
- `python --version` → **Python 3.10.19**
- `pip --version` → **pip 25.3**
- `node --version` → **v22.21.1**
- `npm --version` → **11.4.2**
- `tsc --version` → **5.9.3**

---

## 2) Mapa do projeto (nível alto)

## Pastas/arquivos principais
- `app.py` / `bootstrap.py`: entrypoint(s) do app Python atual
- `mydemands/`: núcleo principal da aplicação MyDemands (domain/infra/services/dashboard/tests)
- `notifications/`: módulos de notificações
- `ai_writing/`: integração de escrita com IA
- `img/`: assets da UI
- `requirements.txt`: dependências Python
- `*.spec` + `build_windows.bat`: empacotamento PyInstaller

## Entry points detectados
- `app.py`
- `mydemands/app.py`

## Organização por camadas (estado atual)
- **Domain:** `mydemands/domain/`
- **Infra:** `mydemands/infra/`
- **Services:** `mydemands/services/`
- **UI/dashboard:** `mydemands/dashboard/`
- **Tests:** `mydemands/tests/`

---

## 3) Status dos comandos de build/test

## Comandos solicitados para web (npm)
Como não existe `package.json`, todos falham com ENOENT:
- `npm run dev` → falha: `Could not read package.json`
- `npm run build` → falha: `Could not read package.json`
- `npm run test` → falha: `Could not read package.json`
- `npm run lint` → falha: `Could not read package.json`

## Baseline executável existente (Python)
- `python -m pytest -q` → **8 passed, 3 skipped**

---

## 4) Riscos e gaps para meta “Web local-first + paridade MyDemands”

1. **Gap estrutural:** não existe app web inicial para evoluir incrementalmente.
2. **Paridade funcional:** regras já existem em módulos Python; será necessário mapear/portar para domínio web sem regressão.
3. **Persistência web local-first:** implementar repositório browser (IndexedDB) e migração de schema.
4. **Import/Export:** reaproveitar contratos atuais (CSV/JSON) garantindo validação centralizada.
5. **Estratégia segura:** manter legado Python intacto e criar vertente web isolada.

---

## 5) Plano em PRs (ajustado ao repo real)

## Estratégia de vertentes
Criar uma nova aplicação em `apps/webdemands` para não quebrar o desktop legado, seguindo as fases pedidas.

### PR #0 (este)
- Baseline técnico + diagnóstico + plano.

### PR #1 — Tooling web reprodutível
- Inicializar `apps/webdemands` (Vite + React + TS).
- Scripts: `dev/build/preview/test/lint/typecheck/clean/check`.
- Config base (`.editorconfig`, `.gitattributes`, `.gitignore` e README local da app web).

### PR #2 — Estrutura + aliases
- `src/app`, `src/domain`, `src/infra`, `src/ui`, `src/shared`.
- aliases TS/Vite e refactor de imports.

### PR #3 — Runbook local
- Documentar setup e troubleshooting para web local-first.

### PRs #4 a #10 — Paridade funcional
- Modelo canônico de Demand.
- Serviços de validação e situação.
- Repositório IndexedDB.
- UI CRUD + filtros + badges com regras do domínio.
- Import/Export com dry-run e relatório.
- Ajustes de contraste dark/light com teste.

### PRs #11 a #13 — Cleanup e hardening
- Remoção segura de código morto com prova de não-uso.
- Eliminar duplicação de regra na UI.
- Estabilidade/performance.

### PR #14 — Release final
- `PARIDADE.md` 100%.
- Documentação final.
- Checklist de build/test/lint/typecheck verde para a app web.

---

## 6) Definition of Done (global, para a vertente web)
- `npm run dev` sobe localmente.
- `npm run build` sem erros críticos.
- `npm run test` verde.
- `npm run lint` verde.
- `npm run typecheck` verde.
- Paridade validada em `PARIDADE.md`.
- Persistência local-first + import/export funcionando.

