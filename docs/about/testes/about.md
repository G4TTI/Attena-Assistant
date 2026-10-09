# Testes — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): organização da suíte (pytest), fixtures compartilhadas, como rodar em container descartável e o mapa arquivo de teste → domínio. Cada domínio lista os seus testes; aqui ficam infraestrutura, convenções e o registro do que foi realmente executado.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/tests/__init__.py`](../../../app/tests/__init__.py) | pendente | 0 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/tests/conftest.py`](../../../app/tests/conftest.py) | Docstring do módulo (não verificada): “Fixtures compartilhadas. Precisa configurar o ambiente ANTES de importar o app.” | 43 função(ões)/método(s) e 2 classe(s) no inventário; relações: pendente |
| [`app/tests/fixtures/schema_v1_3_4.sql`](../../../app/tests/fixtures/schema_v1_3_4.sql) | pendente | ver dados-migracoes; relações: pendente |
| [`app/requirements-dev.txt`](../../../app/requirements-dev.txt) | pendente | relações: pendente |

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
- Dependências compartilhadas (proposta): [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Privacidade](../privacidade/about.md).

## Testes e evidência

Mapa completo arquivo de teste → domínio (cada domínio detalha os seus):

| Arquivo | Funções `test_*` | Domínio |
|---|---|---|
| [`app/tests/test_admin.py`](../../../app/tests/test_admin.py) | 27 | [Administração](../administracao/about.md) |
| [`app/tests/test_api.py`](../../../app/tests/test_api.py) | 18 | [API REST](../api/about.md) |
| [`app/tests/test_app_settings.py`](../../../app/tests/test_app_settings.py) | 6 | [Configurações e Conexões](../configuracoes-conexoes/about.md) |
| [`app/tests/test_billing_plans.py`](../../../app/tests/test_billing_plans.py) | 14 | [Planos e Faturamento](../planos-faturamento/about.md) |
| [`app/tests/test_calendar_api.py`](../../../app/tests/test_calendar_api.py) | 7 | [API REST](../api/about.md) |
| [`app/tests/test_calendar_providers.py`](../../../app/tests/test_calendar_providers.py) | 13 | [Calendário](../calendario/about.md) |
| [`app/tests/test_calendar_service.py`](../../../app/tests/test_calendar_service.py) | 45 | [Calendário](../calendario/about.md) |
| [`app/tests/test_calendar_sync.py`](../../../app/tests/test_calendar_sync.py) | 15 | [Calendário](../calendario/about.md) |
| [`app/tests/test_calendar_web.py`](../../../app/tests/test_calendar_web.py) | 19 | [Calendário](../calendario/about.md) |
| [`app/tests/test_chats.py`](../../../app/tests/test_chats.py) | 13 | [WhatsApp e Conversas](../whatsapp-conversas/about.md) |
| [`app/tests/test_configuracoes.py`](../../../app/tests/test_configuracoes.py) | 9 | [Configurações e Conexões](../configuracoes-conexoes/about.md) |
| [`app/tests/test_logs_privacy.py`](../../../app/tests/test_logs_privacy.py) | 8 | [Privacidade](../privacidade/about.md) |
| [`app/tests/test_media_messages.py`](../../../app/tests/test_media_messages.py) | 31 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_migration_legacy_data.py`](../../../app/tests/test_migration_legacy_data.py) | 3 | [Dados e Migrações](../dados-migracoes/about.md) |
| [`app/tests/test_migration_v14.py`](../../../app/tests/test_migration_v14.py) | 7 | [Dados e Migrações](../dados-migracoes/about.md) |
| [`app/tests/test_multi_tenant_isolation.py`](../../../app/tests/test_multi_tenant_isolation.py) | 3 | [Privacidade](../privacidade/about.md) |
| [`app/tests/test_multi_whatsapp_dispatch.py`](../../../app/tests/test_multi_whatsapp_dispatch.py) | 2 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_onboarding.py`](../../../app/tests/test_onboarding.py) | 24 | [Onboarding e Dashboard](../onboarding-dashboard/about.md) |
| [`app/tests/test_privacy_crypto.py`](../../../app/tests/test_privacy_crypto.py) | 11 | [Privacidade](../privacidade/about.md) |
| [`app/tests/test_privacy_lifecycle.py`](../../../app/tests/test_privacy_lifecycle.py) | 16 | [Privacidade](../privacidade/about.md) |
| [`app/tests/test_recipients.py`](../../../app/tests/test_recipients.py) | 2 | [WhatsApp e Conversas](../whatsapp-conversas/about.md) |
| [`app/tests/test_recurrence.py`](../../../app/tests/test_recurrence.py) | 5 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_scheduled_panel.py`](../../../app/tests/test_scheduled_panel.py) | 33 | [WhatsApp e Conversas](../whatsapp-conversas/about.md) |
| [`app/tests/test_scheduler.py`](../../../app/tests/test_scheduler.py) | 11 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_scheduling_service.py`](../../../app/tests/test_scheduling_service.py) | 30 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_scheduling_ui.py`](../../../app/tests/test_scheduling_ui.py) | 36 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_security_hardening.py`](../../../app/tests/test_security_hardening.py) | 8 | [Autenticação](../autenticacao/about.md) |
| [`app/tests/test_templates_csp.py`](../../../app/tests/test_templates_csp.py) | 4 | [Interface](../interface/about.md) |
| [`app/tests/test_time_sync.py`](../../../app/tests/test_time_sync.py) | 6 | [Arquitetura](../arquitetura/about.md) |
| [`app/tests/test_timing.py`](../../../app/tests/test_timing.py) | 20 | [Agendamentos](../agendamentos/about.md) |
| [`app/tests/test_waha.py`](../../../app/tests/test_waha.py) | 14 | [WhatsApp e Conversas](../whatsapp-conversas/about.md) |
| [`app/tests/test_whatsapp_service.py`](../../../app/tests/test_whatsapp_service.py) | 5 | [WhatsApp e Conversas](../whatsapp-conversas/about.md) |

Total no inventário: 32 arquivos e 466 funções `test_*`. Comando de execução: ver a seção "Testes" do [CLAUDE.md](../../../CLAUDE.md).

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Fixtures de `conftest.py` (banco, chaves de teste, cliente HTTP, WAHA falso).
- Pendente: Última execução da suíte com resultado registrado.
- Pendente: Cenários sem cobertura por domínio.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Privacidade](../privacidade/about.md).
