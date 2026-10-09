# Autenticação — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): cadastro, login/logout, sessões (cookie), recuperação de senha, verificação de e-mail, rate limit das rotas de autenticação, dependências `require_user_*` e checagem de origem (CSRF) aplicada no middleware. As telas de "Minha conta" ficam em configuracoes-conexoes, mas as regras de senha/sessões são descritas aqui.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/auth.py`](../../../app/whatsapp_scheduler/auth.py) | Docstring do módulo (não verificada): “Primitivas de autenticação: hash de senha, sessão (cookie httponly) e tokens de uso único (reset de senha / verificação de e-mail).” | 20 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/auth_service.py`](../../../app/whatsapp_scheduler/auth_service.py) | Docstring do módulo (não verificada): “Regra de negócio de autenticação: cadastro, login, recuperação de senha, verificação de e-mail e auditoria. Equivalente a `calendar_service.py`, mas para con…” | 14 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/ratelimit.py`](../../../app/whatsapp_scheduler/ratelimit.py) | Docstring do módulo (não verificada): “Rate limiting simples em memória (janela fixa) para rotas de autenticação.” | 4 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/auth_routes.py`](../../../app/whatsapp_scheduler/web/auth_routes.py) | Docstring do módulo (não verificada): “UI web de autenticação: login, cadastro, logout, recuperação de senha e verificação de e-mail. Sem rail (usuário ainda não está autenticado) — ver `auth_base…” | 12 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/main.py`](../../../app/whatsapp_scheduler/main.py) | Docstring do módulo (não verificada): “Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app.” | 9 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: só `_origin_check` e `_allowed_hosts`; ver arquitetura; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/auth_base.html`](../../../app/whatsapp_scheduler/web/templates/auth_base.html), [`app/whatsapp_scheduler/web/templates/login.html`](../../../app/whatsapp_scheduler/web/templates/login.html), [`app/whatsapp_scheduler/web/templates/cadastro.html`](../../../app/whatsapp_scheduler/web/templates/cadastro.html), [`app/whatsapp_scheduler/web/templates/esqueci_senha.html`](../../../app/whatsapp_scheduler/web/templates/esqueci_senha.html), [`app/whatsapp_scheduler/web/templates/redefinir_senha.html`](../../../app/whatsapp_scheduler/web/templates/redefinir_senha.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (11; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /login` → `page_login` | pendente | pendente | pendente | pendente |
| `POST /login` → `do_login` | pendente | pendente | pendente | pendente |
| `POST /logout` → `do_logout` | pendente | pendente | pendente | pendente |
| `GET /cadastro` → `page_cadastro` | pendente | pendente | pendente | pendente |
| `POST /cadastro` → `do_cadastro` | pendente | pendente | pendente | pendente |
| `GET /esqueci-senha` → `page_esqueci_senha` | pendente | pendente | pendente | pendente |
| `POST /esqueci-senha` → `do_esqueci_senha` | pendente | pendente | pendente | pendente |
| `GET /redefinir-senha/{token}` → `page_redefinir_senha` | pendente | pendente | pendente | pendente |
| `POST /redefinir-senha/{token}` → `do_redefinir_senha` | pendente | pendente | pendente | pendente |
| `GET /verificar-email/{token}` → `verificar_email` | pendente | pendente | pendente | pendente |
| `POST /verificar-email/reenviar` → `reenviar_verificacao` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Configurações e Conexões](../configuracoes-conexoes/about.md), [Administração](../administracao/about.md), [Privacidade](../privacidade/about.md), [Interface](../interface/about.md), [Arquitetura](../arquitetura/about.md), [Operação](../operacao/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_security_hardening.py`](../../../app/tests/test_security_hardening.py) | Docstring: “Endurecimentos da v1.4: CSRF por Origin, cookies, sessões, auditoria de login sem dado sensível, cabeçalhos e isolamento entre usuários nos recursos novos.” (8 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Contratos de sessão/cookie (`SESSION_COOKIE_NAME`, expiração, revogação).
- Pendente: Regras de rate limit e do cabeçalho de IP do cliente (`CLIENT_IP_HEADER`).
- Pendente: Envio de e-mail de verificação/recuperação e o caminho alternativo pelo CLI.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Configurações e Conexões](../configuracoes-conexoes/about.md), [Administração](../administracao/about.md), [Privacidade](../privacidade/about.md), [Interface](../interface/about.md), [Arquitetura](../arquitetura/about.md), [Operação](../operacao/about.md).
