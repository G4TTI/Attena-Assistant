# Operação — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`.env.example`](../../../.env.example) | 155 |
| [`.gitattributes`](../../../.gitattributes) | 1 |
| [`.gitignore`](../../../.gitignore) | 14 |
| [`README.md`](../../../README.md) | 338 |
| [`app/.dockerignore`](../../../app/.dockerignore) | 10 |
| [`app/Dockerfile`](../../../app/Dockerfile) | 21 |
| [`app/pyproject.toml`](../../../app/pyproject.toml) | 10 |
| [`app/requirements.txt`](../../../app/requirements.txt) | 12 |
| [`app/whatsapp_scheduler/cli.py`](../../../app/whatsapp_scheduler/cli.py) | 250 |
| [`docker-compose.yml`](../../../docker-compose.yml) | 111 |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `_user` |  | [cli.py:47](../../../app/whatsapp_scheduler/cli.py#L47) |  |
| `cmd_generate_keys` |  | [cli.py:55](../../../app/whatsapp_scheduler/cli.py#L55) |  |
| `_read_password` |  | [cli.py:62](../../../app/whatsapp_scheduler/cli.py#L62) | Senha pela entrada padrão (pipe) ou digitada duas vezes no terminal — nunca como argumento de linha de comando (ficaria  |
| `cmd_setup_owner` |  | [cli.py:74](../../../app/whatsapp_scheduler/cli.py#L74) |  |
| `cmd_revoke_admin` |  | [cli.py:87](../../../app/whatsapp_scheduler/cli.py#L87) |  |
| `cmd_reset_link` |  | [cli.py:98](../../../app/whatsapp_scheduler/cli.py#L98) |  |
| `cmd_verify_link` |  | [cli.py:105](../../../app/whatsapp_scheduler/cli.py#L105) |  |
| `_rotate_sealed` |  | [cli.py:111](../../../app/whatsapp_scheduler/cli.py#L111) |  |
| `cmd_rotate_keys` |  | [cli.py:118](../../../app/whatsapp_scheduler/cli.py#L118) |  |
| `cmd_privacy_cleanup` |  | [cli.py:174](../../../app/whatsapp_scheduler/cli.py#L174) |  |
| `cmd_privacy_report` |  | [cli.py:179](../../../app/whatsapp_scheduler/cli.py#L179) |  |
| `cmd_privacy_report.count` | aninhada | [cli.py:185](../../../app/whatsapp_scheduler/cli.py#L185) |  |
| `main` |  | [cli.py:223](../../../app/whatsapp_scheduler/cli.py#L223) |  |
