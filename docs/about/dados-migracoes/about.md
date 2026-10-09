# Dados e Migrações — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): schema (tabelas SQLModel em `models.py`), engine/sessões SQLite, migrações aditivas em `db.py` e migrações de dados versionadas em `migrations.py` (tabela `schema_migrations`). Cada tabela tem as regras descritas no domínio do serviço que a usa; aqui ficam schema, migrações e invariantes de persistência.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/models.py`](../../../app/whatsapp_scheduler/models.py) | Docstring do módulo (não verificada): “Tabelas: `schedules` (a regra) e `dispatches` (cada ocorrência a enviar).” | 14 função(ões)/método(s) e 42 classe(s) no inventário (arquivo inteiro); compartilhado: o schema é descrito aqui; as regras de cada tabela, nos domínios que as usam; relações: pendente |
| [`app/whatsapp_scheduler/db.py`](../../../app/whatsapp_scheduler/db.py) | Docstring do módulo (não verificada): “Engine SQLite + helpers de sessão.” | 7 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/migrations.py`](../../../app/whatsapp_scheduler/migrations.py) | Docstring do módulo (não verificada): “Migrações de DADOS versionadas (tabela `schema_migrations`).” | 10 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/tests/fixtures/schema_v1_3_4.sql`](../../../app/tests/fixtures/schema_v1_3_4.sql) | pendente | schema real da v1.3.4 usado em teste de migração; relações: pendente |

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
- Dependências compartilhadas (proposta): [Privacidade](../privacidade/about.md), [Arquitetura](../arquitetura/about.md), [Operação](../operacao/about.md), [Agendamentos](../agendamentos/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Testes](../testes/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_migration_v14.py`](../../../app/tests/test_migration_v14.py) | Docstring: “Migração v1.4 (privacidade) sobre um banco com o schema REAL da v1.3.4 (tests/fixtures/schema_v1_3_4.sql — só estrutura, sem dados).” (7 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_migration_legacy_data.py`](../../../app/tests/test_migration_legacy_data.py) | Docstring: “v1.3, itens 2 e 45-46 — prova de que a migração para multiusuário nunca perde dado: dados criados ANTES de existir autenticação (user_id NULL) e a sessão WAH…” (3 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido no diff `ca99e37..ab4ce63`: a migração de dados `2026.10.09-media-messages` foi acrescentada a `migrations.py`.
- Pendente: Mapa tabela → domínio dono.
- Pendente: Ordem e idempotência das migrações executadas no arranque.
- Pendente: Restrição do `sqlmodel` e datetimes sem timezone (nota existente no CLAUDE.md; confirmar no código).

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Privacidade](../privacidade/about.md), [Arquitetura](../arquitetura/about.md), [Operação](../operacao/about.md), [Agendamentos](../agendamentos/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Testes](../testes/about.md).
