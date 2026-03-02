# MyDemands - Configuração de IA (OpenAI / Hugging Face)

## Instalação recomendada (Windows, com `venv`)
Para evitar conflitos de dependências globais (especialmente entre `transformers` e `huggingface_hub`), instale sempre em ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

> O `requirements.txt` fixa versões compatíveis, incluindo `transformers==4.57.6` e `huggingface_hub==0.34.4`.

## Build do executável (PyInstaller, zero setup para usuário final)
O executável inclui todas as dependências necessárias (inclusive `cryptography` e bindings nativos), então o usuário final **não precisa** instalar `pip` nem bibliotecas manualmente.

Fluxo recomendado no Windows:

```powershell
build_windows.bat
```

Esse script:

- instala/atualiza dependências de build na `.venv`;
- gera o `dist\DemandasApp.exe` com `app.spec`;
- executa `dist\DemandasApp.exe --self-test-ui` para validar aplicação de tema light/dark e métricas críticas de UI.
- executa `dist\DemandasApp.exe --self-test-crypto` para validar roundtrip AESGCM (cryptography) no bundle.

## Onde fica o arquivo de configuração
As preferências de IA são persistidas em:

- `C:\MyDemands\ai_writing\configIA.txt`

O app cria automaticamente a pasta/arquivo com valores padrão seguros caso não existam.

## Como habilitar e trocar provedor
1. Abra **Configuração de IA** no app.
2. Marque **Habilitar IA**.
3. Em **Provedor de IA**, escolha **OpenAI** ou **Hugging Face**.
4. Preencha os campos do provedor selecionado.
5. Clique em **Testar conexão** e depois em **Salvar**.

> Ao trocar o provedor, os dados do outro provedor não são apagados.

## Chaves/variáveis salvas em `configIA.txt`
```txt
AI_ENABLED=true
AI_PROVIDER=huggingface

# OpenAI
OPENAI_API_KEY=xxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.5
OPENAI_MAX_OUTPUT_TOKENS=300

# Hugging Face
HF_API_TOKEN=xxxx
HF_MODEL=stepfun-ai/Step-3.5-Flash
HF_TEMPERATURE=0.5
HF_MAX_NEW_TOKENS=200
HF_TOP_P=0.9
IA_CACHE_ENABLED=true
```



## Dependências por provider
- **OpenAI**: requer pacote `openai` instalado.
- **Hugging Face**: usa `requests` para chamadas HTTP ao router, sem dependência do pacote `openai`.
- Ao testar conexão, o app valida a dependência correta do provider selecionado e mostra mensagem amigável em caso de ausência.

## Como escolher um modelo no Hugging Face
- Abra a página do modelo no Hugging Face e confira se existe seção **Inference Providers** e/ou **Playground**.
- Copie exatamente o **model id** exibido (ex.: `meta-llama/Llama-3.1-8B-Instruct`).
- Se o modelo não mostrar provider compatível para serverless, ele **não vai funcionar** via `InferenceClient` no app.
- Se aparecer aviso de modelo **gated**/**requires acceptance**, aceite os termos na página do modelo antes de testar no app.

## Observações
- Tokens/chaves são exibidos como campo de senha na tela.
- O app não expõe tokens em logs da funcionalidade.
- **Testar conexão** usa os valores atuais da modal (mesmo sem salvar) e **não** persiste em arquivo.
- O fluxo **Redigir com IA** respeita `AI_ENABLED` e o `AI_PROVIDER` salvo.
- Para Hugging Face, a integração usa chamadas HTTP via `requests` no endpoint Chat Completions do router.

## Matriz de Eisenhower (Consultar Demandas Pendentes)
- A tab **Consultar Demandas Pendentes** possui alternância de visualização: **Padrão** e **Matriz Eisenhower**.
- A preferência é persistida em `ui_prefs.json` na chave `preferences.view.consultar_pendentes`.
- Classificação automática:
  - **Urgente** = `É Urgente? == Sim` **ou** `Timing` em atraso **ou** prazo contendo a data atual.
  - **Importante** = prioridade `Alta` ou `Média` (vazio/inválido cai para `Média`).
  - Quadrantes:
    - Q1: Importante + Urgente
    - Q2: Não importante + Urgente
    - Q3: Importante + Não urgente
    - Q4: Não importante + Não urgente
- Apenas status pendentes/ativos entram na matriz (`Não iniciada`, `Em andamento`, `Bloqueado`, `Requer revisão`).

---

## WebDemands (web local-first) — execução one-command

Esta primeira rodada adiciona uma base web para rodar localmente no navegador, sem backend obrigatório.

### Pré-requisitos
- Node.js 20+

### Comandos (na raiz do repositório)
```bash
npm install
npm run dev
npm run build
npm run test
npm run lint
npm run typecheck
npm run clean
```

### Arquitetura local-first
- Persistência de demandas em IndexedDB (`web/src/db/demandRepository.ts`).
- Import/Export em JSON (camada de repositório + botões na UI).
- Regras centralizadas:
  - validações: `web/src/services/demandValidationService.ts`
  - situação/status: `web/src/services/demandStatusService.ts`

### Troubleshooting rápido
- Se `npm run dev` falhar, confira versão do Node (`node -v`).
- Se testes de UI falharem localmente, reinstale dependências (`npm install`) e rode `npm run test` novamente.
