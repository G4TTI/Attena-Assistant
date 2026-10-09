# Administração — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): área `/admin`: controle de acesso no servidor (conta principal e administradores concedidos por ela), usuários, CRM (status, tags, notas), planos, faturamento, agendamentos (metadados), logins e auditoria — sem decifrar conteúdo de usuário.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/admin/__init__.py`](../../../app/whatsapp_scheduler/admin/__init__.py) | Docstring do módulo (não verificada): “Área administrativa do Attena (/admin).” | 0 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/admin/access.py`](../../../app/whatsapp_scheduler/admin/access.py) | Docstring do módulo (não verificada): “Quem pode administrar e como esse poder é concedido.” | 6 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/admin/security.py`](../../../app/whatsapp_scheduler/admin/security.py) | Docstring do módulo (não verificada): “Controle de acesso do /admin — tudo no servidor.” | 7 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/admin/service.py`](../../../app/whatsapp_scheduler/admin/service.py) | Docstring do módulo (não verificada): “Consultas do admin — só METADADOS, sempre por SELECT de colunas explícitas e devolvendo DTOs (dataclasses). Nenhuma consulta aqui lê conteúdo cifrado, hash d…” | 28 função(ões)/método(s) e 10 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/admin/crm.py`](../../../app/whatsapp_scheduler/admin/crm.py) | Docstring do módulo (não verificada): “CRM administrativo: status comercial, tags e notas internas de cada cliente.” | 14 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/admin_routes.py`](../../../app/whatsapp_scheduler/web/admin_routes.py) | Docstring do módulo (não verificada): “Área administrativa (/admin). Toda rota passa por `admin.security.require_admin` (papel lido do banco, sessão recente, rate limit) e todo POST exige token CSRF.” | 27 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/admin/_base.html`](../../../app/whatsapp_scheduler/web/templates/admin/_base.html), [`app/whatsapp_scheduler/web/templates/admin/_macros.html`](../../../app/whatsapp_scheduler/web/templates/admin/_macros.html), [`app/whatsapp_scheduler/web/templates/admin/dashboard.html`](../../../app/whatsapp_scheduler/web/templates/admin/dashboard.html), [`app/whatsapp_scheduler/web/templates/admin/usuarios.html`](../../../app/whatsapp_scheduler/web/templates/admin/usuarios.html), [`app/whatsapp_scheduler/web/templates/admin/usuario.html`](../../../app/whatsapp_scheduler/web/templates/admin/usuario.html), [`app/whatsapp_scheduler/web/templates/admin/crm.html`](../../../app/whatsapp_scheduler/web/templates/admin/crm.html), [`app/whatsapp_scheduler/web/templates/admin/planos.html`](../../../app/whatsapp_scheduler/web/templates/admin/planos.html), [`app/whatsapp_scheduler/web/templates/admin/faturamento.html`](../../../app/whatsapp_scheduler/web/templates/admin/faturamento.html), [`app/whatsapp_scheduler/web/templates/admin/agendamentos.html`](../../../app/whatsapp_scheduler/web/templates/admin/agendamentos.html), [`app/whatsapp_scheduler/web/templates/admin/logins.html`](../../../app/whatsapp_scheduler/web/templates/admin/logins.html), [`app/whatsapp_scheduler/web/templates/admin/auditoria.html`](../../../app/whatsapp_scheduler/web/templates/admin/auditoria.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (21; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /admin` → `admin_dashboard` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/usuarios` → `admin_users` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/usuarios/{user_id}` → `admin_user_detail` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/status` → `admin_set_crm_status` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/tags` → `admin_add_tag` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/tags/{tag_id}/remover` → `admin_remove_tag` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/notas` → `admin_add_note` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/notas/{note_id}` → `admin_update_note` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/crm/notas/{note_id}/excluir` → `admin_delete_note` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/suspender` → `admin_suspend` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/reativar` → `admin_reactivate` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/usuarios/{user_id}/plano` → `admin_change_plan` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/crm` → `admin_crm` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/crm/tags` → `admin_create_tag` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/crm/tags/{tag_id}/excluir` → `admin_delete_tag` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/planos` → `admin_plans` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `POST /admin/planos/{plan_id}` → `admin_update_plan` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/faturamento` → `admin_finance` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/agendamentos` → `admin_schedules` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/logins` → `admin_logins` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |
| `GET /admin/auditoria` → `admin_audit` | pendente (router com `[Depends(require_admin)]`) | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Autenticação](../autenticacao/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Privacidade](../privacidade/about.md), [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_admin.py`](../../../app/tests/test_admin.py) | Docstring: “Área administrativa: controle de acesso real no servidor, CRM, auditoria e — principalmente — nenhuma forma de ler conteúdo privado dos clientes.” (27 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido em `web/admin_routes.py`: o router é `APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])`, então toda rota declarada nele passa por `require_admin`. O que `require_admin` verifica ainda não foi analisado.
- Pendente: Reautenticação do admin (`AdminReauthRequired` em `main.py`).
- Pendente: O teste estático que garante que `admin/` não decifra conteúdo.
- Pendente: Comandos de CLI que afetam admin (`setup-owner`, `revoke-admin`; ver operacao).

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Autenticação](../autenticacao/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Privacidade](../privacidade/about.md), [Operação](../operacao/about.md), [Dados e Migrações](../dados-migracoes/about.md).
