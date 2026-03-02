# Auditoria inicial WebDemands

## Stack atual detectada
- Aplicação principal atual: Python + PySide6 (desktop), entrada em `app.py`.
- Testes existentes: `pytest` no pacote `mydemands/tests`.
- Build atual: PyInstaller (`build_windows.bat`, `app.spec`).
- Não havia stack web configurada no repositório.

## Problemas encontrados
- Objetivo do projeto exige app web local no navegador, mas o repositório só possuía app desktop.
- Ausência de `package.json`/scripts web (`dev`, `build`, `test`, `lint`, `typecheck`, `clean`).
- Ausência de persistência local web (IndexedDB/localStorage) e fluxo de import/export na camada web.

## Artefatos legados/lixo identificados (não removidos nesta rodada)
- Arquivos de dados e artefatos locais: `notifications.db`, `demandas_export.csv`, `controle_time_2026_02.csv`, `notifications_history.enc.csv`, `ai_writing_audit.sqlite3`, etc.
- Arquivos compilados eventualmente gerados (`__pycache__`), removidos do working tree quando detectados.

## Plano de refatoração (checklist)
- [x] Criar base web local-first (React + Vite + TypeScript).
- [x] Padronizar scripts one-command na raiz (`dev`, `build`, `test`, `lint`, `typecheck`, `clean`).
- [x] Implementar persistência local em IndexedDB com import/export JSON.
- [x] Centralizar regras em serviços (`DemandValidationService`, `DemandStatusService`).
- [x] Criar testes automatizados para validação, status, persistência, import/export e fluxo UI básico.
- [ ] Aproximar integralmente telas/fluxos do MyDemands desktop mantendo paridade funcional total.
- [ ] Revisar/limpar artefatos legados com comprovação de referências e build verde.
- [ ] Adicionar export CSV e refinamentos de UX (filtros/ordenação/edição inline/modal) na web.
