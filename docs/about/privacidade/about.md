# Privacidade — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): cifra de dados de usuário em repouso (conteúdo/destinatários de mensagens programadas, anexos, dados de faturamento e notas), HMAC por usuário, cifra dos tokens OAuth, retenção mínima e expurgo, sanitização de logs e isolamento entre usuários. O documento normativo é [SECURITY_AND_PRIVACY.md](../../SECURITY_AND_PRIVACY.md); este about.md mapeia a implementação e aponta divergências, sem repetir aquele texto.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/privacy.py`](../../../app/whatsapp_scheduler/privacy.py) | Docstring do módulo (não verificada): “Criptografia de dados de usuário em repouso ("Plano A").” | 42 função(ões)/método(s) e 5 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/retention.py`](../../../app/whatsapp_scheduler/retention.py) | Docstring do módulo (não verificada): “Retenção mínima: o conteúdo privado some assim que deixa de ser necessário.” | 23 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/crypto.py`](../../../app/whatsapp_scheduler/crypto.py) | Docstring do módulo (não verificada): “Cifra dos tokens OAuth (Fernet) — nunca guardamos token em texto puro.” | 4 função(ões)/método(s) e 2 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/log_sanitizer.py`](../../../app/whatsapp_scheduler/log_sanitizer.py) | Docstring do módulo (não verificada): “Sanitização central de logs (defesa em profundidade).” | 6 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`docs/SECURITY_AND_PRIVACY.md`](../../../docs/SECURITY_AND_PRIVACY.md) | pendente | documento normativo existente; preservar; relações: pendente |

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
- Dependências compartilhadas (proposta): [Agendamentos](../agendamentos/about.md), [Administração](../administracao/about.md), [Calendário](../calendario/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Operação](../operacao/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_privacy_crypto.py`](../../../app/tests/test_privacy_crypto.py) | Docstring: “privacy.py: AES-256-GCM com AAD por linha, chaves versionadas e HMAC por usuário.” (11 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_privacy_lifecycle.py`](../../../app/tests/test_privacy_lifecycle.py) | Docstring: “Ciclo de vida do conteúdo privado (v1.4):” (16 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_logs_privacy.py`](../../../app/tests/test_logs_privacy.py) | Docstring: “Logs seguros: nem os call sites nem bibliotecas vazam conteúdo, telefone, token, senha, cookie, CPF ou QR — e o sanitizador central pega o que escapar.” (8 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_multi_tenant_isolation.py`](../../../app/tests/test_multi_tenant_isolation.py) | Docstring: “v1.3, item 43 — teste de isolamento consolidado: dois usuários (A e B), cada um com seus próprios WhatsApps/eventos/agendamentos/conexões de calendário, conf…” (3 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido em `main.py` (`lifespan`): `privacy.check_configuration()` roda antes de `init_db()`; o efeito exato quando faltam chaves não foi conferido nesta etapa.
- Pendente: Conferir cada afirmação de SECURITY_AND_PRIVACY.md contra o código atual (inclusive a parte de mídia acrescentada depois da release).
- Pendente: Job `privacy_cleanup`: intervalo, critérios e o que permanece após o expurgo.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Agendamentos](../agendamentos/about.md), [Administração](../administracao/about.md), [Calendário](../calendario/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Operação](../operacao/about.md).
