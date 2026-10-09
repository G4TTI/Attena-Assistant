# Operação — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): implantação e operação: Docker Compose (app + WAHA), imagem, variáveis de ambiente, CLI de servidor, health check, múltiplas instâncias no mesmo host e operações com efeito (chaves, owner, expurgo). As notas operacionais vigentes continuam em CLAUDE.md; este documento referencia, não duplica.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/cli.py`](../../../app/whatsapp_scheduler/cli.py) | Docstring do módulo (não verificada): “Comandos de operação — rodam NO SERVIDOR, por quem tem acesso a ele:” | 13 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/config.py`](../../../app/whatsapp_scheduler/config.py) | Docstring do módulo (não verificada): “Configuração via variáveis de ambiente (12-factor).” | 1 função(ões)/método(s) e 1 classe(s) no inventário; variáveis de ambiente; cada domínio consome as suas; relações: pendente |
| [`app/whatsapp_scheduler/main.py`](../../../app/whatsapp_scheduler/main.py) | Docstring do módulo (não verificada): “Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app.” | 9 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: só `healthz`; relações: pendente |
| [`docker-compose.yml`](../../../docker-compose.yml) | pendente | relações: pendente |
| [`.env.example`](../../../.env.example) | pendente | nomes de variáveis; nunca copiar o `.env` real; relações: pendente |
| [`app/Dockerfile`](../../../app/Dockerfile) | pendente | relações: pendente |
| [`app/.dockerignore`](../../../app/.dockerignore) | pendente | relações: pendente |
| [`app/requirements.txt`](../../../app/requirements.txt) | pendente | relações: pendente |
| [`app/pyproject.toml`](../../../app/pyproject.toml) | pendente | versão do app (subir junto com `main.py`); relações: pendente |
| [`README.md`](../../../README.md) | pendente | relações: pendente |
| [`.gitignore`](../../../.gitignore) | pendente | relações: pendente |
| [`.gitattributes`](../../../.gitattributes) | pendente | relações: pendente |

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (1; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /healthz` → `healthz` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Arquitetura](../arquitetura/about.md), [Privacidade](../privacidade/about.md), [Administração](../administracao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Testes](../testes/about.md).

## Testes e evidência

Nenhum arquivo de teste atribuído a este domínio.

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido em `cli.py` (`main`): subcomandos `generate-keys`, `setup-owner`, `revoke-admin`, `reset-link`, `verify-link`, `rotate-keys`, `privacy-cleanup` e `privacy-report`; todos exceto `generate-keys` chamam `privacy.check_configuration()` e `init_db()` antes de rodar. Efeitos de cada um: pendente.
- Divergência lida: `README.md` diz "Versão alfa 1.2" e a seção "Estrutura" cita `CachedMessage`/"histórico com cache"; no commit-base a versão em `main.py` e `app/pyproject.toml` é `1.4.0` e `models.py` não define `CachedMessage`.
- Pendente: Lista completa de variáveis (`config.py` × `.env.example` × `docker-compose.yml`).
- Pendente: Procedimento de implantação da v1.4 na instância oficial (chaves próprias, backup, `setup-owner`).
- Pendente: Operações perigosas: `rotate-keys`, `privacy-cleanup`, migração no arranque.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Arquitetura](../arquitetura/about.md), [Privacidade](../privacidade/about.md), [Administração](../administracao/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Testes](../testes/about.md).
