# Attena Assistant

_Versão alfa 1.2_

Agendador de mensagens de WhatsApp com **WAHA** como motor de envio.
Você cria agendamentos numa página web (ou pela API REST) e um _poller_ interno
dispara cada mensagem quando o horário agendado alcança o horário real — incluindo
recorrências (cron / diário / semanal) e mensagens que ficaram atrasadas por uma
queda do serviço.

```
Navegador ──▶ FastAPI (app) ──▶ SQLite (data/app.db)
              ├─ UI web (Jinja2 + htmx)     schedules  = a regra
              ├─ API REST (/api/*)          dispatches = cada ocorrência
              └─ poller (a cada TICK_SECONDS):
                   1. materializa a próxima ocorrência de cada regra
                   2. envia as dispatches vencidas  ──▶  WAHA ──▶ WhatsApp
```

## Requisitos

- Docker + Docker Compose
- Um número de WhatsApp para parear (de preferência **dedicado** — veja _Riscos_)

## Subindo

```bash
cp .env.example .env
```

Edite o `.env` e defina uma `WAHA_API_KEY` forte (e as senhas do dashboard).
Opcionalmente gere tudo com o utilitário do WAHA:

```bash
docker run --rm -v "$PWD/waha:/app/env" devlikeapro/waha init-waha /app/env
```

Depois:

```bash
docker compose up -d --build
```

- App: <http://localhost:8000>
- Dashboard nativo do WAHA: <http://localhost:3000/dashboard>

## Parear o WhatsApp

1. Abra <http://localhost:8000>. O painel "Sessão WhatsApp" vai aparecer como
   `SCAN_QR_CODE` com um QR code.
2. No celular: WhatsApp → **Aparelhos conectados** → **Conectar um aparelho** →
   escaneie o QR.
3. O painel muda para **conectado** (`WORKING`). Pronto para agendar.

O login fica salvo no volume `./waha/sessions`, então sobrevive a `docker compose
restart`.

## Usando

A interface tem uma barra lateral com cinco telas:

| Tela | O que faz |
|---|---|
| **📅 Agendamentos** | Cria (destinatários pela lista de contatos, WhatsApp, data/hora, várias mensagens), lista e abre o detalhe de cada agendamento; no detalhe: **Editar**, **Cancelar** e **Enviar agora**. |
| **💬 Conversas** | Lista as conversas do WhatsApp; abre o histórico de cada uma e permite **enviar agora** ou **agendar** uma mensagem para aquele contato/grupo sem sair da tela. |
| **🔌 Sessão** | Status da conexão + QR de pareamento. |
| **🗓️ Calendário** | Agenda de eventos internos e sincronizados do Google Agenda; permite associar uma automação de WhatsApp a qualquer evento. |
| **⚙️ Configurações** | "Calendários conectados" — conectar/desconectar o Google Agenda, escolher quais calendários sincronizar, sincronizar manualmente. |

### Conversas

Visual no estilo WhatsApp Web: lista de conversas à esquerda (com foto, quando o
WAHA retorna uma) e o histórico + composer à direita.

- **Busca:** o campo no topo da lista filtra por nome/prévia da última mensagem,
  em tempo real, no navegador (sem round-trip ao servidor).
- A lista de chats vem do WAHA (`chats/overview`) com cache curto em memória.
- O histórico de cada conversa fica em cache local (`cached_messages` no SQLite):
  a primeira abertura pode levar **até ~1 min** no engine `WEBJS`; as seguintes
  são instantâneas. O botão **↻** no cabeçalho força nova busca.
- **Composer:** caixa de texto + botão verde de enviar (envia na hora, `POST
  /api/sendText`) + ícone **🕐** que abre o painel **Agendar mensagens**: uma
  data/hora de início e uma **sequência** de mensagens (adicionar/mover/excluir).
  O horário digitado vale para o agendamento inteiro e nunca é reiniciado ao
  adicionar mensagens.
- **Mensagens agendadas dentro da conversa:** cada uma aparece como uma bolha
  própria com o status (🕐 agendada · ⏳ enviando · ✓ enviada · ⚠ falhou · ○
  cancelada) e o horário real do disparo, no seu fuso. Dá para cancelar uma
  por uma. As já enviadas viram bolhas normais do histórico, marcadas "agendada".
- Para histórico bem mais rápido, troque o engine para `NOWEB` no `.env`
  (`WHATSAPP_DEFAULT_ENGINE=NOWEB`) — exige parear de novo.

### Pela interface

Escolha o(s) destinatário(s) na lista de contatos (com foto; também aceita um
número digitado + Enter), o WhatsApp de envio (só os seus, com status ao vivo —
um WhatsApp desconectado não deixa agendar), data/hora do primeiro envio e as
mensagens. **Opções avançadas** guarda a recorrência (só para agendamentos de
**uma** mensagem). O fuso é o da sua conta (Configurações → Preferências) — não
é um campo do formulário. Um agendamento por destinatário; cada um é uma
sequência de mensagens enviadas na ordem (intervalo de 3 s entre elas).

### Pela API

```bash
# criar (disparo único)
curl -X POST http://localhost:8000/api/schedules -H 'Content-Type: application/json' -d '{
  "recipient": "+55 11 99999-8888",
  "text": "Olá! Lembrete: reunião às 15h.",
  "send_at": "2026-09-12T14:55:00",
  "timezone": "America/Sao_Paulo"
}'

# criar (recorrente)
curl -X POST http://localhost:8000/api/schedules -H 'Content-Type: application/json' -d '{
  "recipient": "5511999998888",
  "text": "Bom dia! ☀️",
  "send_at": "2026-09-11T09:00:00",
  "recurrence": "daily 09:00"
}'

curl http://localhost:8000/api/schedules                 # listar
curl -X DELETE http://localhost:8000/api/schedules/{id}   # cancelar
curl -X POST http://localhost:8000/api/schedules/{id}/run-now   # disparar já
curl http://localhost:8000/api/session                    # status da sessão WAHA
```

**Formato do destinatário:** telefone internacional (`+55 11 99999-8888`,
`5511999998888`) ou um `chatId` do WhatsApp já pronto (`5511999998888@c.us`,
`...@g.us` para grupo). Números sem DDI são interpretados como **Brasil**.

**Uma mensagem = um agendamento de uma mensagem.** A API continua agendando uma
mensagem por chamada (`POST /api/schedules`); cada uma vira um agendamento
(`ScheduleGroup`) de uma mensagem, exatamente como o que a interface cria.

**Recorrência:** expressão `cron` de 5 campos **ou** um atalho:
`daily HH:MM` · `weekly <dia> HH:MM` · `monthly <D> HH:MM` · `hourly`.
(`<dia>`: `mon`/`seg`/`segunda`…)

## Modelo de agendamento (v1.3.3)

Conversas, Agendamentos e as automações do Calendário usam **o mesmo modelo e o
mesmo código**:

- **`ScheduleGroup`** = um agendamento: usuário, destinatário, WhatsApp
  (`session`), horário de início (`start_local` + `timezone`), origem
  (`manual` · `conversation` · `calendar`) e a sequência de mensagens
  (`Schedule` com `group_id` + `position`). O status do agendamento não é
  guardado — é derivado dos `Dispatch`es (`schedule_views.py`).
- **`timing.py`** é a única fonte de cálculo de horário: horário digitado →
  UTC (via `ZoneInfo`, nunca "+3h" na mão), intervalo antes/depois do evento,
  intervalo personalizado `HH:MM`, horário de cada mensagem da sequência.
- **`service.py`** é a única porta de escrita: `create_sequence`,
  `update_sequence`, `reschedule_group`, `cancel_schedule(s)`/`cancel_group`,
  `run_group_now`. O motor (`scheduler.py`) só enxerga `Schedule`/`Dispatch`.
- **Ordem da sequência:** a mensagem *N+1* só é liberada depois que a *N* é
  confirmada como enviada (`ScheduleDependency`). Cancelar uma do meio religa as
  seguintes; falha definitiva aborta as seguintes (nunca saem fora de ordem).
- **Fuso:** o horário é sempre digitado e exibido no fuso do usuário; no banco
  fica `first_run_local` + `timezone` (agendamentos) e UTC (dispatches).
- Migração automática no boot (`service.backfill_groups`): agendamentos criados
  antes da v1.3.3 ganham um grupo, sem apagar nada.

**Intervalo personalizado (Calendário):** em *Quando enviar* → Antes/Depois do
evento, *Intervalo* → **Personalizado…** aceita `HH:MM` (`1:45` = 1 h 45 min
antes/depois do evento — é uma distância do evento, não um horário do relógio).
"Horário fixo no dia do evento" continua existindo para um horário absoluto.

## Como o disparo funciona

- A cada `TICK_SECONDS` (padrão 30s) o poller compara `scheduled_at <= agora`.
  Precisão do envio ≈ o valor do tick.
- **Sessão fora do ar** (celular offline, logout): a dispatch fica pendente e é
  reavaliada no próximo tick, **sem gastar tentativa**.
- **Falha de envio:** re-tentativa com backoff (`60s → 5min → 15min`, configurável),
  até `max_attempts`; depois marca `failed`.
- **Atraso longo:** dispatch mais atrasada que `MAX_OVERDUE_MINUTES` (padrão 120)
  é marcada `skipped` em vez de disparar em avalanche quando o serviço volta.
- **Reinício abrupto:** dispatches presas em `processing` são recuperadas
  automaticamente.

## Calendário (Google Agenda)

Integração opcional e desligada por padrão — o app funciona normalmente sem
ela. Quando configurada, permite:

1. Conectar uma conta Google (OAuth oficial, só leitura — escopo
   `calendar.readonly`; a senha do Google **nunca** passa pelo app).
2. Escolher quais calendários da conta sincronizar.
3. Ver os eventos desses calendários na tela **Calendário**, junto com
   eventos internos.
4. Associar uma automação de WhatsApp a qualquer evento: destinatário(s),
   mensagem e uma regra de tempo ("2 horas antes", "30 minutos depois" etc.) —
   isso cria um agendamento normal na tela **Agendamentos**, usando o mesmo
   sistema de disparo/retentativa já existente.

A sincronização de um evento **nunca** envia mensagem sozinha — só cria uma
automação quando o usuário pede explicitamente. Se o evento mudar de horário
no Google, o agendamento já criado é **recalculado no mesmo lugar** (sem
duplicar); se o evento for cancelado, qualquer mensagem ainda pendente é
cancelada, preservando o histórico do que já foi enviado.

Arquitetura preparada para outros provedores (Outlook, Apple/iCloud) via uma
camada de abstração (`calendar_providers/`), mas só o Google está
implementado por enquanto.

**Para ativar:** crie um OAuth Client em
[console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
(tipo "Web application", redirect URI = `GOOGLE_OAUTH_REDIRECT_URI` abaixo) e
preencha as variáveis da seção "Google Calendar" no `.env` — veja
`.env.example` para o passo a passo completo, incluindo o comando para gerar
`TOKEN_ENCRYPTION_KEY`. Sem essas variáveis, a tela **Configurações** mostra
exatamente o que falta configurar, em vez de quebrar.

## Configuração (`.env`)

| Variável | Padrão | Efeito |
|---|---|---|
| `WAHA_API_KEY` | — | Chave compartilhada entre WAHA e app (obrigatória) |
| `WAHA_SESSION` | `default` | Nome da sessão do WhatsApp no WAHA |
| `WHATSAPP_DEFAULT_ENGINE` | `WEBJS` | `WEBJS` (compatível) · `NOWEB` (leve) · `GOWS` |
| `TICK_SECONDS` | `30` | Intervalo de verificação do poller |
| `MAX_OVERDUE_MINUTES` | `120` | Atraso máximo antes de `skipped` |
| `DEFAULT_TIMEZONE` | `America/Sao_Paulo` | Fuso quando o agendamento não informa um |
| `SEND_JITTER_SECONDS` | `1.5` | Pausa (com jitter) entre envios consecutivos |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | — | Credenciais OAuth do Google Calendar (opcional) |
| `GOOGLE_OAUTH_REDIRECT_URI` | `http://localhost:8090/calendario/oauth/callback` | Precisa bater com o registrado no Google Cloud Console |
| `TOKEN_ENCRYPTION_KEY` | — | Chave Fernet para cifrar os tokens salvos (obrigatória para conectar o Google) |
| `CALENDAR_SYNC_SECONDS` | `300` | Intervalo da sincronização automática com o Google Calendar |

## Riscos e limites

- **API não-oficial do WhatsApp.** Envio automatizado — sobretudo em volume ou
  para contatos novos — pode levar ao **banimento do número**. Use um número
  dedicado, mantenha volume baixo e o jitter ligado.
- **Uma instância só.** O SQLite pressupõe um único processo escritor (o poller).
  Não rode o serviço `app` replicado. Para alta disponibilidade, migrar para
  Postgres + `SELECT ... FOR UPDATE SKIP LOCKED`.
- **Backup:** copie o volume `./data` (`app.db` + arquivos `-wal`/`-shm`).
- **Número brasileiro sem entrega:** alguns números antigos exigem o dígito 9
  ausente/presente. Se um envio falhar com "número não existe", teste o `chatId`
  manualmente no dashboard do WAHA.
- **Espaço em disco.** O WAHA (`WEBJS`) roda um Chromium e o Docker Desktop
  guarda a imagem/VM no disco do sistema. Com o disco cheio a sessão vira
  `FAILED` e o `docker build` falha com `read-only file system`. No Windows dá
  para mover a imagem do Docker: *Settings → Resources → Advanced → Disk image
  location*.

## Aplicar mudanças de código sem rebuild

O `docker-compose.yml` monta `./app/whatsapp_scheduler` dentro do container. Como
nenhuma dependência nova foi adicionada, basta reiniciar:

```bash
docker compose restart app
```

Só é preciso `--build` ao mexer no `requirements.txt` ou no `Dockerfile`.

## Desenvolvimento

```bash
cd app
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

Rodar o app sem Docker (precisa de um WAHA acessível em `WAHA_BASE_URL`):

```bash
cd app
WAHA_BASE_URL=http://localhost:3000 WAHA_API_KEY=xxx uvicorn whatsapp_scheduler.main:app --reload
```

## Estrutura

```
whatsapp-scheduler/
├── docker-compose.yml          # waha + app
├── .env.example
├── data/                       # volume: app.db (SQLite)
├── waha/sessions/              # volume: login do WhatsApp
└── app/
    ├── Dockerfile
    ├── requirements.txt
    └── whatsapp_scheduler/
        ├── main.py             # FastAPI + lifespan (sobe o poller)
        ├── config.py           # env vars
        ├── db.py               # engine SQLite (WAL)
        ├── models.py           # ScheduleGroup, Schedule, Dispatch, CachedMessage, ...
        ├── timing.py           # regras de TEMPO (única fonte de cálculo de horário)
        ├── recurrence.py       # presets/cron + fuso
        ├── recipients.py       # telefone -> chatId
        ├── waha.py             # cliente HTTP do WAHA (sessão, envio, chats)
        ├── scheduler.py        # materialize_due / dispatch_due / loop
        ├── service.py          # regras de agendamento (criar/editar/cancelar/remarcar) — API + UI + Calendário
        ├── schedule_views.py   # leitura: status e horário real de cada mensagem/agendamento
        ├── chatsvc.py          # conversas: lista + histórico com cache
        ├── crypto.py           # cifra (Fernet) dos tokens OAuth salvos
        ├── calendar_providers/ # abstração de provedor de calendário (base.py + google.py)
        ├── calendar_service.py # regras de calendário (conectar, automações)
        ├── calendar_sync.py    # sincronização com o provedor + loop de background
        ├── calendar_schemas.py # DTOs de leitura (nunca expõem token)
        ├── api/                # /api/schedules, /api/session, /api/chats, /api/calendar
        └── web/                # UI (Jinja2 + htmx): agendamentos, conversas, sessão, calendário, configurações
```
