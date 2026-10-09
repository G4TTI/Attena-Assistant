# Interface — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): layout e componentes compartilhados (Jinja2 + HTMX + JavaScript inline): `base.html`, macros de `_components.html`, status da barra lateral, convenções HTMX e a política de CSP que os templates precisam respeitar. Blocos de tela específicos pertencem aos domínios das telas.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/web/templates/base.html`](../../../app/whatsapp_scheduler/web/templates/base.html) | pendente | compartilhado: layout e JavaScript inline de várias telas; dividir os blocos por domínio na etapa 2; relações: pendente |
| [`app/whatsapp_scheduler/web/templates/_components.html`](../../../app/whatsapp_scheduler/web/templates/_components.html) | pendente | compartilhado: macros; o campo de anexo é regra de agendamentos; relações: pendente |
| [`app/whatsapp_scheduler/web/routes.py`](../../../app/whatsapp_scheduler/web/routes.py) | Docstring do módulo (não verificada): “UI web (Jinja2 + htmx, sem build step).” | 56 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: só `ui_sidebar_status`; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/_sidebar_status.html`](../../../app/whatsapp_scheduler/web/templates/_sidebar_status.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (1; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /ui/sidebar-status` → `ui_sidebar_status` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Arquitetura](../arquitetura/about.md), [Agendamentos](../agendamentos/about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Autenticação](../autenticacao/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_templates_csp.py`](../../../app/tests/test_templates_csp.py) | Docstring: “O app manda `Content-Security-Policy: script-src 'self' https://unpkg.com 'unsafe-inline'` (sem 'unsafe-eval'). O htmx avalia filtros de trigger (`hx-trigger…” (4 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Inventário estático: 64 funções JavaScript nomeadas em templates (`templates[].named_js_functions`), a maior parte em `base.html`.
- Pendente: Mapa bloco de JS → domínio.
- Pendente: Contratos HTMX compartilhados (eventos, `hx-target`, OOB, atualização automática).
- Pendente: Cabeçalhos de segurança/CSP efetivos (`_security_headers` em `main.py`).

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Arquitetura](../arquitetura/about.md), [Agendamentos](../agendamentos/about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Autenticação](../autenticacao/about.md).
