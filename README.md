# Verificador de Processos (LLM) — JUSCASH Machine Learning Case - Victor Tintel

- API + UI para validar, via LLM, se um processo judicial atende às políticas de compra de crédito da Juscash.
- Inclui: FastAPI com documentação Swagger, Streamlit UI, seleção de provedor de LLM por ambiente (Groq, Ollama, OpenAI), exemplos de JSON, Dockerfiles, docker-compose, e deploy no Render
----------------------------------------------------------------
## Sumário
- Arquitetura
- Como funciona (resumo)
- Estrutura do repositório
- Endpoints da API
- Políticas e Prompt
- Variáveis de ambiente
- Rodando localmente (sem Docker)
- Rodando com Docker Compose
- UI (Streamlit)
- Exemplos (cURL e Swagger)
- Deploy no Render (API)
- Deploy no Render (UI)
- Observabilidade básica (opcional)
- Debug e Troubleshooting
- Checklist do case
- Licença
-------------------------------------------------------------
## Arquitetura
             ┌──────────────┐
             │  Streamlit   │  → UI para colar o JSON e ver a resposta
             └─────┬────────┘
                   │  (HTTP)
                   ▼
            ┌──────────────┐
            │   FastAPI    │  → /predict, /docs, /health, /debug/llm
            └─────┬────────┘
                  │
    ┌─────────────┼─────────────────────────┐
    │             │                         │
    ▼             ▼                         ▼
  Groq        Ollama (local)              OpenAI
 (SaaS)       (localhost:11434)           (SaaS)
 
- O provedor/LLM é selecionado por variáveis de ambiente.
- A API é stateless.
- A UI chama a API (não contém lógica de LLM).
-------------------------------------------------------------------------------------
## Como funciona
- A UI (ou o cliente via Swagger/cURL) envia o payload mínimo de um processo para POST /predict.
- A API chama o LLM com um prompt contendo as políticas (POL-1..POL-8) e as orientações de formato.
- O LLM responde com JSON válido com as chaves exigidas:

{
  "decision": "approved" | "rejected" | "incomplete",
  "rationale": "string",
  "citacoes": ["POL-1", "DOC-1-2", "..."]
}
------------------------------------------------------------------------------------------
## Estrutura do repositório
.
├─ app/

│  ├─ main.py          # FastAPI (endpoints /health, /predict, /debug/llm)

│  └─ llm.py           # client LLM (Groq, Ollama, OpenAI) + validação JSON

│  └─ orchestration.py   # Envio de logs para n8n/Langsmith

│  └─ policy.py       # Funções utilitárias(Checagens POL-1...POL-8)

│  └─ schemas.py      # Pydantic: Processo/Documento/Movimento + Saída

│  └─ settings.py     # Configs por env vars (Modelo LLM, URLs etc...)

├─ .venv

├─ ui/

│  └─ app.py   # Streamlit (define API_BASE_URL via ENV)

│

├─ prompts/

│  └─ v1.md            # POL-1..POL-8 + formato de saída exigido

│

├─ data/

│  └─ samples/         # 3 JSONs de exemplo (contrato mínimo)

│

├─ tests/              # (espaço para testes; se houver)

├─ .env.example        # template de variáveis de ambiente

├─ requirements.txt    # dependências (API e UI)

├─ Dockerfile.api      # imagem da API (FastAPI/uvicorn)

├─ Dockerfile.ui       # imagem da UI (Streamlit)

├─ docker-compose.yml  # sobe API + (opcional) Ollama + UI, localmente

└─ README.md


--------------------------------------------------------------------------------------------
## Endpoints da API
- Base local: http://localhost:8000
- Docs: /docs
- GET /health → {"status": "ok"}
- POST /predict → recebe o JSON do processo e retorna a decisão (ver formato acima)
- GET /debug/llm → inspeção rápida do provider/modelo e se a chave do provedor existe:

{"provider":"groq","model":"llama3-8b-8192","has_key": true}

--------------------------------------------------------------------------------------------
## Políticas e Prompt
- As políticas (POL-1..POL-8) e as instruções de formato vivem em prompts/v1.md.
- O llm.py concatena as políticas e orienta o modelo a retornar JSON estrito (sem comentários, sem texto extra).
- O main.py valida o JSON antes de responder (evita “alucinações” de formato).
-------------------------------------------------------------------------------------------
## Variáveis de ambiente
Crie um .env a partir de .env.example.

Comuns à API
- Variável	Descrição	Exemplo
LLM_PROVIDER	groq, ollama ou openai	groq
LLM_MODEL	Modelo do provedor	llama3-8b-8192 (Groq)
N8N_WEBHOOK_URL	(Opcional) URL para observabilidade básica	https://seu-n8n/webhook/xyz

- Se LLM_PROVIDER=groq:

Variável	Descrição	Exemplo
GROQ_API_KEY	chave da API Groq	gsk_...

- Se LLM_PROVIDER=openai:

Variável	Descrição	Exemplo
OPENAI_API_KEY	chave OpenAI	sk-...

- Se LLM_PROVIDER=ollama:

Variável	Descrição	Exemplo
OLLAMA_BASE_URL	URL do daemon do Ollama	http://localhost:11434

- Nota: Para rodar com Ollama, faça pull de um modelo antes (ex.: ollama pull llama3.2:1b).

Comuns à UI (Streamlit)
- Variável	Descrição	Exemplo
API_BASE_URL	Base da API a ser chamada pela UI	http://localhost:8000 ou URL do Render

-------------------------------------------------------------------------------------------------
## Rodando localmente (sem Docker)

-- Requisitos: Python 3.11+ --

### Clone e prepare o ambiente
- git clone https://github.com/victortintel/juscash-ml-case.git
- cd juscash-ml-case
- cp .env.example .env


### Instale dependências

- pip install -r requirements.txt


### Configure o provedor (edite .env)

#### Ex.: Groq

- LLM_PROVIDER=groq
- LLM_MODEL=llama3-8b-8192
- GROQ_API_KEY=...sua chave...


#### Ex.: Ollama local

- LLM_PROVIDER=ollama
- LLM_MODEL=llama3.2:1b
- OLLAMA_BASE_URL=http://localhost:11434


### Suba a API

- uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

- Abra http://localhost:8000/docs (Swagger).

### (Opcional) Suba a UI

- export API_BASE_URL="http://localhost:8000"
- streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0
- Abra http://localhost:8501.

------------------------------------------------------------------------------------
## Rodando com Docker Compose
#### Requisitos: Docker Desktop + Docker Compose

- docker compose up --build
- A primeira chamada a /predict pode baixar o modelo (se usar Ollama); aguarde o pull nos logs.

#### Endpoints:
- API: http://localhost:8000
- UI : http://localhost:8501
- Se quiser forçar Groq no compose, defina LLM_PROVIDER=groq, LLM_MODEL=llama3-8b-8192, GROQ_API_KEY=... no arquivo de ambiente lido pelo serviço da API.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
## UI (Streamlit)
#### A UI é simples e objetiva:
- campo para colar o JSON do processo;
- botão Analisar que chama POST /predict;
- mostra a resposta formatada;
- exibe, no topo esquerdo, a API que está sendo usada (lida de API_BASE_URL).
- Em ambiente serverless (Render com plano Free), a UI faz um ping ao /health para “acordar” a API antes do /predict.
- Mesmo assim, a primeira chamada pode demorar — é o cold start do provedor/infra.

--------------------------------------------------------------------------------------------------------------------------------
## Exemplos (cURL e Swagger)

#### Swagger: http://localhost:8000/docs ou https://<sua-api>.onrender.com/docs

curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "numeroProcesso": "0001234-56.2023.4.05.8100",
    "siglaTribunal": "TRF5",
    "esfera": "Federal",
    "valorCondenacao": 67592,
    "documentos": [
      {"id": "DOC-1-2", "nome": "Certidão de Trânsito em Julgado", "texto": "Certifico o trânsito em julgado."},
      {"id": "DOC-1-4", "nome": "Requisição (RPV)", "texto": "Expede-se RPV em favor do exequente."}
    ],
    "movimentos": []
  }'

### Resposta (exemplo):

{
  "decision": "approved",
  "rationale": "POL-1: Só compramos crédito de processos transitados em julgado e em fase de execução.",
  "citacoes": ["POL-1","DOC-1-2"]
}

-------------------------------------------------------------------------------------------------------------
## Deploy no Render (API)

O repositório está pronto para deploy sem Docker no Render (também funciona com Dockerfile.api, mas a versão sem Docker é mais simples).

1- Create → Web Service (GitHub: victortintel/juscash-ml-case)

2- Branch: main • Region: Oregon (US West) • Instance Type: Free

3- Build Command: pip install -r requirements.txt

4- Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

5- Health check path: /health

6- Environment → Add variables:
- LLM_PROVIDER=groq
- LLM_MODEL=llama3-8b-8192
- GROQ_API_KEY=...
- (Opcional) N8N_WEBHOOK_URL=https://seu-n8n/webhook/xyz
- Observação: no plano Free há cold start. A primeira requisição pode demorar.

-------------------------------------------------------------------------------------------------------------------
## Deploy no Render (UI)

Também use deploy sem Docker, apontando a UI para a API.

1- Create → Web Service (mesmo repositório)

2- Build Command: pip install -r requirements.txt

3- Start Command: streamlit run ui/app.py --server.port=$PORT --server.address=0.0.0.0

4- Environment → Add variable: API_BASE_URL=https://<seu-servico-api>.onrender.com

5- Acesse a URL gerada do serviço da UI.

---------------------------------------------------------------------------------------------------------------
## Observabilidade básica (opcional)

Logo após calcular a decisão em POST /predict, se N8N_WEBHOOK_URL estiver setada, a API envia:

{
  "input": { ...payload original... },
  "output": { ...decisão JSON... },
  "provider": "groq",
  "model": "llama3-8b-8192"
}

- Timeout: 10s (não quebra a API se o webhook falhar).
- Útil para ter “rastro” de uso sem depender de logs do provedor.
----------------------------------------------------------------------------------------------------------------
