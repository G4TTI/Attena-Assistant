# Attena Assistant — índice da documentação técnica

Agendador de mensagens de WhatsApp multiusuário (FastAPI, SQLModel/SQLite,
Jinja2/HTMX, JavaScript inline, Docker Compose, WAHA, Google Calendar). Antes de
usar este índice, leia a [política de documentação](docs/DOCUMENTATION_POLICY.md):
abra só os domínios que a tarefa afeta e confirme no código o que for importante.

## Base

- Revisão documentada: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc`
  (`feature/v1.4-criptografia`, 2026-10-09). É um commit **local, ainda sem push**.
- Release de referência: tag `1.4-criptografia` =
  `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34` (= `origin/feature/v1.4-criptografia`).
- Diferença `ca99e37..ab4ce63` (1 commit, lido no diff): agendamento de mídia —
  foto/vídeo/áudio/PDF, recurso de plano (`media.py`, tabela `media_attachments`,
  `Schedule.media_id`, migração `2026.10.09-media-messages`, rotas `/ui/media*`,
  `waha.py`, `privacy.py`, `retention.py`, templates e testes). Ver
  [Agendamentos](docs/about/agendamentos/about.md).
- `main` e `origin/main` estão 31 commits atrás de `ca99e37` e **não** refletem a
  versão atual.

## Estado

Etapa 1: política, modelo, inventário e estrutura criados. **Nenhum domínio foi
levantado ainda**; todos estão `pendente` e trazem só o mapeamento inicial de
arquivos, rotas e testes (mais alguns fatos pontuais marcados "Lido"). O
levantamento completo é a etapa 2. A divisão abaixo é uma proposta.

| Domínio | Escopo proposto | Estado |
|---|---|---|
| [arquitetura](docs/about/arquitetura/about.md) | ciclo de vida do app, routers, middlewares, relógio, erros compartilhados | pendente |
| [autenticacao](docs/about/autenticacao/about.md) | cadastro, login, sessões, senha, verificação de e-mail, rate limit, CSRF | pendente |
| [onboarding-dashboard](docs/about/onboarding-dashboard/about.md) | primeiros passos, bloqueio de onboarding, Dashboard | pendente |
| [whatsapp-conversas](docs/about/whatsapp-conversas/about.md) | conexões WhatsApp/WAHA, Conversas, painel de programadas | pendente |
| [configuracoes-conexoes](docs/about/configuracoes-conexoes/about.md) | página Configurações: conta, calendários conectados, fuso | pendente |
| [agendamentos](docs/about/agendamentos/about.md) | modelo de agendamento, tempo/recorrência, scheduler, mídia | pendente |
| [calendario](docs/about/calendario/about.md) | Google Calendar, sincronização, eventos, automações | pendente |
| [planos-faturamento](docs/about/planos-faturamento/about.md) | planos, limites, upgrade, faturamento, webhook | pendente |
| [administracao](docs/about/administracao/about.md) | `/admin`: acesso, usuários, CRM, planos, auditoria | pendente |
| [dados-migracoes](docs/about/dados-migracoes/about.md) | schema, engine, migrações aditivas e de dados | pendente |
| [privacidade](docs/about/privacidade/about.md) | cifra, retenção/expurgo, logs, isolamento | pendente |
| [interface](docs/about/interface/about.md) | `base.html`, componentes, HTMX/JS compartilhado, CSP | pendente |
| [api](docs/about/api/about.md) | REST `/api/*` e DTOs | pendente |
| [operacao](docs/about/operacao/about.md) | Docker, variáveis, CLI, health check, implantação | pendente |
| [testes](docs/about/testes/about.md) | suíte pytest, fixtures, mapa teste → domínio | pendente |

## Arquivos compartilhados

Cada regra é descrita no domínio dono; os demais apontam para ele.

| Arquivo | Divisão por seção/símbolo |
|---|---|
| `app/whatsapp_scheduler/main.py` | `lifespan`, `app`, handlers de exceção, `_security_headers` → arquitetura; `_origin_check`, `_allowed_hosts` → autenticacao; `_needs_onboarding`, `_onboarding_gate` → onboarding-dashboard; `healthz` → operacao |
| `app/whatsapp_scheduler/web/routes.py` | página `/agendamentos`, seções "Agendamentos" e "Anexos" → agendamentos; páginas `/conversas*`, seções "Conversas" e "Conversas: painel" → whatsapp-conversas; `ui_sidebar_status` → interface; "Contextos e entradas compartilhados": a dividir |
| `app/whatsapp_scheduler/web/settings_routes.py` | rotas → configuracoes-conexoes; regras de senha/sessões → autenticacao; OAuth/sincronização → calendario |
| `app/whatsapp_scheduler/models.py` | schema → dados-migracoes; regras de cada tabela → domínio do serviço que a usa (mapa a fazer) |
| `app/whatsapp_scheduler/config.py` | variáveis → operacao; cada domínio cita as que consome |
| `app/whatsapp_scheduler/crypto.py` | privacidade (cifra dos tokens OAuth usados por calendario) |
| `app/whatsapp_scheduler/cli.py` | operacao; efeitos em admin, chaves e expurgo descritos em administracao/privacidade |
| `web/templates/base.html`, `_components.html` | interface; blocos de JS e macros de tela → domínio da tela (a dividir) |
| `api/*.py` | contrato REST → api; regras → domínio correspondente |

## Inventário estático

Gerado por [`docs/about/build_inventory.py`](docs/about/build_inventory.py) sobre
`ab4ce63` (AST, sem importar o app): 171 arquivos rastreados, 64 módulos Python
do app, 835 funções/métodos e 115 classes do app, 30 tabelas SQLModel, 137 rotas
declaradas (23 em `/api/`), 60 templates com 64 funções JS nomeadas, 32 arquivos
de teste com 466 funções `test_*`, 0 divergências de integridade. Detalhes em
[`INVENTARIO.json`](docs/about/INVENTARIO.json) e [`ROTAS.md`](docs/about/ROTAS.md).

## Divergências conhecidas

- `README.md` desatualizado (versão "alfa 1.2" e `CachedMessage` na estrutura):
  detalhe em [operacao](docs/about/operacao/about.md). O README não foi alterado
  nesta etapa.

## Outros documentos

- [CLAUDE.md](CLAUDE.md): notas operacionais e armadilhas vigentes.
- [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md): documento
  normativo de segurança e privacidade.
- [docs/about/MODELO-about.md](docs/about/MODELO-about.md): modelo dos about.md de domínio.
