# Attena Assistant — notas do projeto

Agendador de mensagens de WhatsApp multiusuário (FastAPI + SQLModel/SQLite +
HTMX) com integração ao Google Agenda. O envio passa pelo WAHA.

## Branches e versões

- O trabalho atual é no branch `feature/v1.4-criptografia` (a partir de
  `feature/v1.3-multiusuario`, tags `1.3.x`).
- O `main` está parado na alfa 1.2 e **não** reflete a versão atual.
- A versão aparece em `app/whatsapp_scheduler/main.py` (`FastAPI(version=...)`)
  e `app/pyproject.toml`; suba as duas juntas.

## Rodar mais de uma instância no mesmo servidor

Oficial e teste rodam no mesmo host. Tudo que poderia colidir vem do `.env`,
com padrões iguais aos da oficial (o `docker-compose.yml` serve às duas sem
edição):

| Variável | Oficial (padrão) | Por quê |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `attena-assistant` | rede/projeto do compose |
| `WAHA_CONTAINER_NAME` / `APP_CONTAINER_NAME` | `waha-scheduler` / `whatsapp-scheduler` | nomes de container são globais no Docker |
| `WAHA_HOST_PORT` / `APP_HOST_PORT` | `3001` / `8090` | portas do host |
| `SESSION_COOKIE_NAME` | `attena_session` | cookies **não separam por porta**; mesmo nome = uma instância desloga a outra. O cookie de state do OAuth é derivado dele |

Nunca escreva valores de teste direto no `docker-compose.yml`.

## Armadilhas conhecidas

- **`sqlmodel` fixado em `<=0.0.42`**: a 0.0.47 rejeita datetimes sem timezone
  e o scheduler quebra (Internal Server Error). Para liberar, o código precisa
  gravar datetimes com timezone primeiro.
- **Pasta `data/`** precisa pertencer ao uid 999 (usuário `app` do container);
  se o Docker criar como root, o SQLite não abre ("unable to open database file").
- **Google OAuth**: o Google só aceita redirect `localhost` ou domínio HTTPS
  (nunca IP da rede). O fluxo precisa começar e terminar no mesmo host do
  `GOOGLE_OAUTH_REDIRECT_URI`, senão os cookies de sessão/state não voltam.
- **Atrás do Cloudflare** use `CLIENT_IP_HEADER=CF-Connecting-IP`, senão todos
  os visitantes dividem o mesmo rate limit de login/cadastro.
- O painel do WAHA só escuta em `127.0.0.1` e, desde a v1.4, o dashboard/Swagger
  ficam desligados por padrão (`WAHA_DASHBOARD_ENABLED=false`): eles leem conversas.
- **Chaves de dados (v1.4):** `DATA_ENCRYPTION_KEYS` e `DATA_HASH_KEY` são
  obrigatórias — sem elas o app não sobe. Cada ambiente tem as suas (teste ≠
  oficial); gerar com `python -m whatsapp_scheduler.cli generate-keys`. Nunca
  commitar nem imprimir.
- **Privacidade (v1.4):** conteúdo/destinatário de mensagens programadas só
  cifrados (`privacy.py`) e expurgados ao terminar (`retention.py`); conversas são
  só visuais (nada de histórico no banco); o pacote `admin/` nunca decifra conteúdo
  (há teste estático). Ver `docs/SECURITY_AND_PRIVACY.md` antes de mexer nisso.
- **Migrações de dados** ficam em `migrations.py` (tabela `schema_migrations`); as
  aditivas continuam em `db.py`. Em teste, descarte o pool (`engine.dispose()`)
  depois de trocar o schema por fora, senão conexões antigas veem o schema velho.
- Admin só pelo CLI no servidor: `cli grant-admin <e-mail>` / `revoke-admin`.
  Sem provedor de e-mail, links de senha: `cli reset-link <e-mail>`.

## Testes

Rodar num container descartável, sem sujar o código montado:

```bash
docker run --rm --user 0 -v "$PWD/app:/w" -w /w --entrypoint sh <imagem-do-app> -c "pip install -q -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider; find /w -name __pycache__ -prune -exec rm -rf {} +"
```

O código é montado no container (`./app/whatsapp_scheduler`); para aplicar
mudanças de Python basta `docker compose restart app`. Mudou
`requirements.txt` → `docker compose up -d --build app`.
