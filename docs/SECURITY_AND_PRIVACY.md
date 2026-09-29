# Attena Assistant — Segurança e Privacidade (v1.4)

Este documento descreve **o que o Attena guarda, o que não guarda, como protege o
que guarda e por quanto tempo**. Ele é técnico e deliberadamente honesto sobre os
limites — nenhuma afirmação aqui deve ser lida como "zero-knowledge" ou "E2EE".

> **Resumo em uma frase:** o Attena não é um banco de conversas. Ele guarda, cifrado,
> apenas o necessário para entregar mensagens programadas, e apaga o conteúdo assim
> que a mensagem deixa de precisar dele. O servidor de produção tem uma chave e
> consegue decifrar quando precisa operar — por isso quem administra o servidor
> **e** tem a chave é o limite de confiança.

---

## 1. Princípios

| Princípio | Como aparece no código |
|---|---|
| Privacy by Design | Conversas são só visuais (`chatsvc.py`); não existe tabela de histórico. |
| Minimização | Cadastro pede só nome, e-mail e senha. Dados de faturamento só no upgrade. |
| Retenção mínima | Conteúdo apagado no mesmo commit em que a mensagem termina (`retention.py`). |
| Menor privilégio | O admin vê metadados; não há rota nem função que decifre conteúdo para ele. |

## 2. Modelo de ameaça ("Plano A")

O servidor guarda uma chave de dados **fora do banco** e decifra um dado somente
quando precisa: entregar uma mensagem no WhatsApp ou mostrá-la ao próprio dono.

| Quem / o quê | Consegue ler conteúdo de mensagens? |
|---|---|
| Banco de dados sozinho (arquivo `app.db`, dump, backup) | **Não** — só ciphertext AES-GCM e hashes HMAC. |
| Painel administrativo `/admin` | **Não** — não há tela, rota ou função para isso (testado). |
| Logs da aplicação | **Não** — call sites só registram metadados + sanitizador central. |
| Suporte / CRM | **Não** — notas do CRM têm aviso e bloqueio de texto de conversa. |
| Desenvolvedor sem acesso às chaves de produção | **Não** (as chaves ficam só no `.env`/secret do servidor). |
| Quem tem shell root no servidor de produção **e** a chave | **Sim.** Este é o limite do Plano A. |
| Quem tem a `WAHA_API_KEY` e acesso à rede interna do WAHA | **Sim** — o WAHA é o WhatsApp do usuário (ver §8). |

## 3. Dados que o Attena ARMAZENA

| Dado | Onde | Forma | Enquanto |
|---|---|---|---|
| Nome, e-mail, telefone da conta | `users` | texto (necessário para login/contato) | a conta existir |
| Senha | `users.password_hash` | **Argon2id** (irreversível) | a conta existir |
| Sessão de login | `user_sessions.token_hash` | SHA-256 do token (o token só existe no cookie) | até expirar/revogar + 30 dias |
| IP / navegador de login e sessão | `login_audit_events`, `user_sessions` | texto | **30 dias** (`LOGIN_IP_RETENTION_DAYS`) |
| Registro de login (sem IP) | `login_audit_events` | metadados | **180 dias** |
| Conteúdo de mensagem programada | `schedules.message_ciphertext` + `encryption_nonce` + `encryption_key_version` | **AES-256-GCM** | até a mensagem terminar |
| Destinatário (chatId/telefone) | `schedules.recipient_phone_encrypted`, `schedule_groups.recipient_encrypted` | **AES-256-GCM** | até o agendamento terminar |
| Hash do destinatário | `*.recipient_phone_hash` | **HMAC-SHA256** por usuário | fim do agendamento + **30 dias** |
| Texto das automações do Calendário | `automation_messages.message_ciphertext` | **AES-256-GCM** | enquanto alguma entrega da automação estiver ativa |
| Id da mensagem no WAHA (embute telefone) | `dispatches.waha_message_hash` | **HMAC** | + 30 dias após o fim |
| Status/horários/tentativas/código de erro | `dispatches` | metadados | indefinido (métricas) |
| Tokens Google OAuth | `calendar_connections.*_token_enc` | **Fernet** (`TOKEN_ENCRYPTION_KEY`) | até desconectar (aí apagados e revogados) |
| Eventos do Google Agenda sincronizados | `events` (título, descrição, horário) | texto | janela de sync (−90 / +365 dias) |
| Dados de faturamento | `billing_profiles.*_encrypted` | **AES-256-GCM** (UF e 2 últimos dígitos do CPF em claro) | até o usuário remover |
| Planos, assinaturas, pagamentos | `plans`, `subscriptions`, `payments` | metadados financeiros (sem cartão) | indefinido (contábil) |
| CRM (status, tags) | `crm_profiles`, `crm_tags`, `crm_user_tags` | metadados | indefinido |
| Notas internas do CRM | `crm_notes.body_encrypted` | **AES-256-GCM** | até excluir |
| Auditoria administrativa | `admin_audit_log` | metadados (sem conteúdo) | indefinido |

## 4. Dados que o Attena NÃO armazena

- **Mensagens recebidas** (0 dias) — nem no banco, nem em arquivo, nem em log.
- **Histórico de conversas** (0 dias) — a tabela `cached_messages` da v1.3 foi removida.
- **Mídias** (imagem, áudio, vídeo, documento) — nunca baixadas (`downloadMedia=false`,
  `WAHA_API_DOWNLOAD_MEDIA=false`).
- **Agenda de contatos do WhatsApp** — consultada ao vivo, só em memória.
- **Fotos de perfil** — são URLs do próprio WhatsApp que o navegador carrega direto.
- **Conteúdo de mensagem enviada/cancelada/falha/ignorada** — apagado ao terminar.
- **Número de cartão, CVV, validade, senha de cartão** — responsabilidade do gateway.
- **E-mail digitado em login que falhou**.
- **Tokens, senhas, cookies, QR Code, links de redefinição** — nunca em log.

### Cache em memória (não é armazenamento)

`chatsvc.py` mantém em RAM, por usuário/WhatsApp/conversa: a lista de conversas
(TTL **20 s**) e o histórico aberto (TTL **60 s**), para a tela não esperar o WEBJS
a cada atualização. Entradas vencidas são **removidas** (não só ignoradas) em toda
leitura e a cada tick do scheduler (30 s). Reiniciar o processo apaga tudo.

## 5. Criptografia

- **Algoritmo:** AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`),
  nonce aleatório de 96 bits por operação. Nada implementado à mão.
- **AAD (dado associado):** `attena:<tabela.coluna>:<id da linha>`. Um ciphertext
  copiado para outra linha (de outro usuário, por exemplo) **não decifra** — em vez de
  ser enviado pelo WhatsApp errado.
- **Formato:**
  - mensagens: três colunas (`message_ciphertext`, `encryption_nonce`, `encryption_key_version`);
  - demais campos: envelope `v<versão>:<nonce b64>:<ciphertext b64>` numa coluna `*_encrypted`.
- **Chaves versionadas:** `DATA_ENCRYPTION_KEYS="1:<b64>,2:<b64>"`. Dado novo usa a
  maior versão (ou `DATA_ENCRYPTION_ACTIVE_VERSION`); as anteriores só decifram.
  Rotação: adicionar versão nova → reiniciar → `python -m whatsapp_scheduler.cli rotate-keys`
  → depois de conferir, remover a versão antiga.
- **Índice cego:** HMAC-SHA256 com chave própria (`DATA_HASH_KEY`), sobre
  `"recipient" | user_id | chatId`. Não é SHA-256 puro (sem a chave não dá para
  testar números por força bruta) e o mesmo número gera hashes diferentes em contas
  diferentes (não dá para cruzar clientes).
- **Sem chave, sem app:** `privacy.check_configuration()` roda no boot; sem as chaves
  (ou com chave inválida) o processo não sobe.
- **Tokens do Google:** Fernet (AES-128-CBC + HMAC-SHA256) com `TOKEN_ENCRYPTION_KEY`
  — mantido da v1.3 (mecanismo maduro), chave separada.
- **Em memória:** o texto decifrado para envio vive só dentro de
  `scheduler._send_one` e as referências são descartadas logo após a chamada ao WAHA.
  Python não garante zerar a memória de uma `str`; isso é uma limitação conhecida.
- **Arquivo do banco:** `PRAGMA secure_delete=ON` zera páginas de conteúdo apagado; a
  migração da v1.4 roda `VACUUM` + checkpoint do WAL (verificado: ids de chat no
  arquivo do banco de teste caíram de 1.800 ocorrências para 0).

## 6. Ciclo de vida de uma mensagem programada

```
criação ──► PENDING (cifrada: texto + destinatário)
              │
              ├─ na hora: worker lê o ciphertext → decifra EM MEMÓRIA → envia ao WAHA
              │           → descarta o texto → grava só metadados
              │
              ├─ SENT ─────────────┐
              ├─ CANCELLED ────────┤  mesmo commit: message_ciphertext, encryption_nonce,
              ├─ FAILED (final) ───┤  encryption_key_version, recipient_phone_encrypted = NULL;
              └─ SKIPPED ──────────┘  content_purged_at = agora; destinatário do agendamento
                                      apagado quando TODAS as mensagens dele terminaram.
```

- Falha com nova tentativa (retry) mantém o conteúdo até a última tentativa.
- **Recorrência:** o conteúdo existe enquanto a regra estiver ativa; cancelar/excluir
  apaga na hora.
- **Automação:** excluir/editar a automação, excluir o evento ou desconectar a conta
  Google cancela as entregas e apaga os textos.
- **Conta suspensa:** as mensagens não saem (status `skipped`, código
  `account_suspended`) e o conteúdo é expurgado.
- Histórico operacional que sobra: ids, dono, horários, status, tentativas,
  `failure_code` e um texto de erro sanitizado. Métricas saem daí.

## 7. Retenção e o job `privacy_cleanup`

Roda no boot e a cada `PRIVACY_CLEANUP_SECONDS` (padrão 1 h), e pelo CLI
(`cli privacy-cleanup`). Registra apenas `records_cleaned=N` por categoria.

| Verificação | Ação |
|---|---|
| mensagem encerrada ainda com ciphertext/destinatário | apaga |
| agendamento sem mensagem ativa ainda com destinatário cifrado | apaga |
| texto de automação sem entrega ativa (após 10 min de carência) | apaga |
| hash de destinatário / id WAHA de algo encerrado há +30 dias | apaga (NULL) |
| IP/navegador de login e de sessão com +30 dias | apaga |
| registro de login com +180 dias | exclui |
| sessão encerrada/expirada há +30 dias | exclui |
| token de reset/verificação usado ou expirado há +7 dias | exclui |
| conexão Google desconectada ainda com token | apaga os tokens |
| WhatsApp desconectado ainda presente no WAHA | logout + delete da sessão no WAHA |
| caches em memória vencidos (conversas, rate limit) | remove |

## 8. WAHA — o que ele guarda (limitação real, não escondida)

Versão em uso no teste: **WAHA 2026.8.2 CORE, engine WEBJS**. Volume: `./waha/sessions`.

1. **O que persiste no volume:** `waha.sqlite3` (configuração das sessões) e, por
   sessão, o **perfil completo do Chromium do WhatsApp Web** (`session-<nome>/Default`):
   IndexedDB (~185 MB no teste), Cache (~57 MB), Service Worker, cookies, Local Storage.
2. **Mantém mensagens/chats localmente?** **Sim, no engine WEBJS.** O WhatsApp Web
   guarda no IndexedDB do navegador as conversas recentes, contatos e chaves — é assim
   que o WhatsApp Web funciona em qualquer computador. O WAHA não oferece opção para
   desligar isso no WEBJS.
3. **Configuração para desabilitar persistência de mensagens:** existe no engine
   **NOWEB** (`config.noweb.store.enabled=false`, que o Attena agora usa por padrão —
   antes era `true`). Com o store desligado, o NOWEB guarda só credenciais; porém a
   lista de conversas e o histórico da tela Conversas deixam de funcionar nesse engine
   (o envio continua). O engine GOWS tem opções de armazenamento próprias que não
   foram avaliadas nesta versão.
4. **Manter só as credenciais?** Com NOWEB e store desligado: sim. Com WEBJS: não.
5. **O engine atual cria cache/histórico?** Sim (item 2).

Mitigações aplicadas na v1.4:
- dashboard e Swagger do WAHA **desligados por padrão** (`WAHA_DASHBOARD_ENABLED=false`,
  `WHATSAPP_SWAGGER_ENABLED=false`) — eles permitiam ler todas as conversas;
- API do WAHA só em `127.0.0.1` + rede interna do Docker, com `WAHA_API_KEY`;
- `WAHA_PRINT_QR=False`, `WAHA_LOG_LEVEL=warn`, log de acesso HTTP abaixo do limiar
  (URLs com chatId não vão para o log), mídia nunca baixada;
- desconectar um WhatsApp no Attena agora faz **logout e apaga a sessão no WAHA**
  (credenciais e perfil local saem do volume);
- rotação de logs do Docker (10 MB × 3) nos dois containers.

Recomendações: trate `./waha/sessions` e a `WAHA_API_KEY` como segredos de produção;
não inclua `waha/sessions` em backups externos sem criptografia; avalie NOWEB (sem
store) se a tela Conversas puder ser dispensada.

## 9. Google OAuth

- Tokens cifrados (Fernet) em `calendar_connections`; nunca vão para o navegador
  (DTOs `calendar_schemas.py` não os incluem) nem para o log (URLs sem query, erros sem
  corpo de resposta, `_tokens_from_response` não imprime a resposta).
- Cookie de `state` do OAuth: HttpOnly, SameSite=Lax, Secure quando aplicável.
- Desconectar: tokens apagados do banco na hora e revogação no Google (best-effort).
- Isolamento: toda conexão/calendário/evento é consultado com o `user_id` do dono.

## 10. Senhas, sessões e CSRF

- Argon2id (`argon2-cffi`, parâmetros padrão da biblioteca); nunca em log.
- Cookie de sessão: HttpOnly, SameSite=Lax, Secure em produção (ou `SESSION_COOKIE_SECURE=true`),
  expira em 30 dias; logout revoga no servidor; trocar a senha encerra os outros dispositivos;
  redefinir a senha encerra todas as sessões.
- CSRF: SameSite=Lax + verificação de `Origin`/`Referer` em todo POST/PUT/PATCH/DELETE
  + token CSRF (HMAC ligado à sessão) em todo formulário do `/admin`.
- Rate limit: login/cadastro/esqueci-senha (5 / 5 min) e por admin no `/admin`.
- Links de redefinição/verificação **não vão para o log**. Sem provedor de e-mail, o
  operador gera com `cli reset-link <e-mail>` / `cli verify-link <e-mail>`.

## 11. Multi-tenancy

- Toda entidade tem dono (`user_id`) direto ou pela cadeia (evento → automação,
  agendamento → mensagem → dispatch); toda rota filtra pelo usuário da sessão, nunca
  por dado vindo do navegador. Ids de outro usuário respondem 404 (não revelam existência).
- O HMAC do destinatário é por usuário: mesmo com acesso ao banco não se relaciona o
  mesmo contato entre contas.
- RLS: não se aplica — o banco é SQLite (não tem Row Level Security). O isolamento é
  na camada de serviço e está coberto por testes (`test_multi_tenant_isolation.py`,
  `test_security_hardening.py`, `test_privacy_lifecycle.py`).

## 12. Administração (`/admin`)

- Papel `admin` só pelo servidor: `docker compose exec app python -m whatsapp_scheduler.cli grant-admin <e-mail>`
  (e `revoke-admin`). Nenhuma tela/API promove alguém a admin.
- Validação no servidor a cada requisição (papel lido do banco). Quem não é admin
  recebe 404; cookie/header/query/localStorage com "admin" não mudam nada (testado).
- Sessão de admin com idade máxima (`ADMIN_SESSION_MAX_AGE_HOURS`, padrão 12 h): depois
  disso é preciso entrar de novo. **MFA:** não implementado — recomendado TOTP
  (`pyotp`) + códigos de recuperação, com o segredo cifrado pela mesma chave de dados;
  o ponto de entrada já existe (`admin/security.py::_check`).
- O que o admin vê: contas, datas, contagens, status, planos, assinaturas, pagamentos,
  CPF **mascarado** (`***.***.***-25`, sem decifrar nada), UF, códigos de erro sanitizados.
- O que o admin **não** vê: conteúdo de mensagens, conversas, histórico, mídia,
  telefone de destinatários, endereço, CPF completo, tokens.
- Teste estático garante que o pacote `admin/` não usa nenhuma função que decifre
  conteúdo de usuário (`test_admin.py::test_admin_code_never_touches_decryption_of_user_content`).

## 13. Auditoria

`admin_audit_log`: `admin_id`, `action`, `target_type`, `target_id`, `created_at` e um
`detail` curto e não sensível (ex. `{"from": "lead", "to": "ativo"}`; para notas, só o id).
Ações registradas: status do CRM, tags (criar/aplicar/remover/excluir), notas
(criar/alterar/excluir), suspender/reativar conta, alterar plano manualmente, editar
plano do catálogo. Tela: Admin › Auditoria.

## 14. Faturamento

- Dados de faturamento pedidos **só** no upgrade (nunca no cadastro), cifrados; o dono
  pode removê-los em Planos (se não houver assinatura paga em curso).
- Sem gateway configurado (`PAYMENT_PROVIDER` vazio): o upgrade para em
  "Pagamento ainda não configurado", a assinatura fica `incomplete` e **nada** é cobrado
  ou marcado como pago.
- Faturamento/MRR vêm só de `payments.status = paid` e de assinaturas ativas de um
  gateway real (`billing/metrics.py`). Assinaturas "manual" (cortesia do admin) nunca
  contam como receita. Nunca "usuários × preço".
- Integração futura: implementar `billing/gateway.PaymentGateway` e registrar em
  `_REGISTRY`; o webhook `/billing/webhook/<provedor>` valida a assinatura e chama
  `service.apply_gateway_event` (idempotente por id do pagamento).

## 15. Backups

- O banco (`data/app.db`) não contém conversas nem conteúdo em texto puro: backups
  herdam isso. Conteúdo ativo, destinatários, faturamento e notas saem **cifrados**.
- **Guarde as chaves separadas dos backups.** Backup + chave juntos = conteúdo legível.
  Backup sem a chave = inútil para restaurar mensagens pendentes (por isso guarde a
  chave também, offline, em outro lugar).
- Tokens do Google no backup: cifrados com `TOKEN_ENCRYPTION_KEY` (mesma regra).
- `waha/sessions`: contém credenciais do WhatsApp e o cache do WhatsApp Web (§8) —
  tratar como segredo; não copiar para serviços externos sem criptografia.
- Backups **anteriores à v1.4** (ex. `backup-pre-v1.4-*`) contêm o texto puro antigo e
  a tabela `cached_messages`: devem ser apagados assim que a v1.4 for validada.

## 16. Gestão de segredos

| Segredo | Onde | Quem deve ter |
|---|---|---|
| `DATA_ENCRYPTION_KEYS`, `DATA_HASH_KEY` | `.env` do servidor ou arquivo (`*_FILE`, ex. Docker secret) | só o servidor de produção + cópia offline do dono |
| `TOKEN_ENCRYPTION_KEY` | idem | idem |
| `WAHA_API_KEY` | idem | idem |
| `GOOGLE_CLIENT_SECRET` | idem | idem |

- Nunca no Git (`.env` está no `.gitignore`), nunca na documentação, nunca no navegador,
  nunca no banco.
- **Cada ambiente com as suas** (desenvolvimento, teste, produção): gere com
  `python -m whatsapp_scheduler.cli generate-keys`. Um desenvolvedor local usa chaves
  locais e não recebe as de produção.
- Perder a chave de dados = perder as mensagens pendentes e os dados de faturamento
  (não há recuperação — por design).
