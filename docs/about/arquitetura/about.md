# Arquitetura — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): visão geral dos módulos e do ciclo de vida do app: criação do FastAPI e registro dos routers, `lifespan` (inicialização, rotinas de arranque e serviços de fundo), middlewares/handlers transversais, fonte única de tempo e erros compartilhados. Regras de cada área ficam nos domínios específicos.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/__init__.py`](../../../app/whatsapp_scheduler/__init__.py) | Docstring do módulo (não verificada): “Agendador de mensagens WhatsApp sobre o WAHA.” | 0 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/__init__.py`](../../../app/whatsapp_scheduler/web/__init__.py) | pendente | 0 função(ões)/método(s) e 0 classe(s) no inventário; pacote vazio; relações: pendente |
| [`app/whatsapp_scheduler/main.py`](../../../app/whatsapp_scheduler/main.py) | Docstring do módulo (não verificada): “Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app.” | 9 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: `lifespan`, `app`, handlers de exceção e `_security_headers` aqui; `_origin_check`/`_allowed_hosts` → autenticação; `_needs_onboarding`/`_onboarding_gate` → onboarding; `healthz` → operação; relações: pendente |
| [`app/whatsapp_scheduler/clock.py`](../../../app/whatsapp_scheduler/clock.py) | Docstring do módulo (não verificada): “Fonte de tempo única do app.” | 3 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/time_sync.py`](../../../app/whatsapp_scheduler/time_sync.py) | Docstring do módulo (não verificada): “Sincroniza `clock.utcnow()` com um horário de referência da internet.” | 5 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/errors.py`](../../../app/whatsapp_scheduler/errors.py) | Docstring do módulo (não verificada): “Erros de domínio compartilhados (ficam aqui pra `timing.py`, `service.py` e o resto poderem levantá-los sem import circular).” | 0 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |

## Contratos de telas e APIs

Nenhuma rota HTTP declarada nos arquivos deste domínio. Pontos de entrada não HTTP (jobs, CLI, arranque): pendente.

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Privacidade](../privacidade/about.md), [Autenticação](../autenticacao/about.md), [Interface](../interface/about.md), [Agendamentos](../agendamentos/about.md), [Calendário](../calendario/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_time_sync.py`](../../../app/tests/test_time_sync.py) | pendente (sem docstring de módulo) (6 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido em `main.py` (`lifespan`): a ordem de arranque é `log_sanitizer.install` → `privacy.check_configuration` → `init_db` → `ClockSyncService.start` → rotinas de dados (`calendar_service.migrate_legacy_automations`, `whatsapp_service.migrate_legacy_sessions`, `service.backfill_groups`, `onboarding_service.migrate_legacy_users`, `app_settings.load_from_db`, `plans.seed_default_plans`, `plans.ensure_admin_plan`, `admin_crm.seed_default_tags`) → `SchedulerService`, `CalendarSyncService` e `PrivacyCleanupService` iniciados; no desligamento, param em ordem inversa e o cliente WAHA é fechado. O comportamento de cada etapa não foi analisado.
- Lido em `main.py`: 13 routers registrados com `include_router`, sem prefixo extra (os prefixos vêm dos próprios `APIRouter`).
- Pendente: Diagrama de dependências entre módulos.
- Pendente: Comportamento dos middlewares e handlers de exceção.
- Pendente: Política de concorrência entre os serviços de fundo e as requisições.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Privacidade](../privacidade/about.md), [Autenticação](../autenticacao/about.md), [Interface](../interface/about.md), [Agendamentos](../agendamentos/about.md), [Calendário](../calendario/about.md).
