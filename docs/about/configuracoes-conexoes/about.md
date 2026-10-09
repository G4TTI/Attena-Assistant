# Configurações e Conexões — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): página Configurações: "Minha conta" (perfil, troca de senha, sair de outros dispositivos), "Calendários conectados" (início do OAuth do Google, callback, ativar calendário, sincronizar, desconectar), "Preferências" (fuso do usuário) e relógio. Esta página é o ponto de entrada; as regras de senha/sessões estão em autenticacao e as de OAuth/sincronização em calendario.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/web/settings_routes.py`](../../../app/whatsapp_scheduler/web/settings_routes.py) | Docstring do módulo (não verificada): “UI web da página Configurações: "Minha conta" (perfil/segurança), "Calendários conectados" (Google Agenda) e "Preferências" (fuso horário do próprio usuário…” | 16 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/app_settings.py`](../../../app/whatsapp_scheduler/app_settings.py) | Docstring do módulo (não verificada): “Configurações persistidas em runtime (hoje: só o fuso horário global).” | 3 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/configuracoes.html`](../../../app/whatsapp_scheduler/web/templates/configuracoes.html), [`app/whatsapp_scheduler/web/templates/_connections.html`](../../../app/whatsapp_scheduler/web/templates/_connections.html), [`app/whatsapp_scheduler/web/templates/_preferences.html`](../../../app/whatsapp_scheduler/web/templates/_preferences.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (12; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /configuracoes` → `page_configuracoes` | pendente | pendente | pendente | pendente |
| `GET /ui/configuracoes/connections` → `ui_connections` | pendente | pendente | pendente | pendente |
| `POST /configuracoes/preferencias/timezone` → `ui_set_timezone` | pendente | pendente | pendente | pendente |
| `GET /ui/configuracoes/relogio` → `ui_clock` | pendente | pendente | pendente | pendente |
| `POST /configuracoes/google/connect` → `connect_google` | pendente | pendente | pendente | pendente |
| `GET /calendario/oauth/callback` → `google_oauth_callback` | pendente | pendente | pendente | pendente |
| `POST /ui/configuracoes/calendars/{calendar_id}/toggle` → `ui_toggle_calendar` | pendente | pendente | pendente | pendente |
| `POST /ui/configuracoes/connections/{connection_id}/sync` → `ui_sync_now` | pendente | pendente | pendente | pendente |
| `POST /ui/configuracoes/connections/{connection_id}/disconnect` → `ui_disconnect` | pendente | pendente | pendente | pendente |
| `POST /configuracoes/conta/perfil` → `ui_update_profile` | pendente | pendente | pendente | pendente |
| `POST /configuracoes/conta/senha` → `ui_change_password` | pendente | pendente | pendente | pendente |
| `POST /configuracoes/conta/sair-outros-dispositivos` → `ui_logout_other_sessions` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Autenticação](../autenticacao/about.md), [Calendário](../calendario/about.md), [Arquitetura](../arquitetura/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Interface](../interface/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_configuracoes.py`](../../../app/tests/test_configuracoes.py) | pendente (sem docstring de módulo) (9 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_app_settings.py`](../../../app/tests/test_app_settings.py) | pendente (sem docstring de módulo) (6 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Fronteira proposta: as conexões WhatsApp (página `/whatsapps`) estão em whatsapp-conversas; confirmar se essa divisão atende.
- Pendente: Relação entre fuso global e fuso do usuário em `app_settings`.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Autenticação](../autenticacao/about.md), [Calendário](../calendario/about.md), [Arquitetura](../arquitetura/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Interface](../interface/about.md).
