"""Tabelas: `schedules` (a regra) e `dispatches` (cada ocorrência a enviar)."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .clock import utcnow


def _uuid() -> str:
    return str(uuid4())


class DispatchStatus(str, enum.Enum):
    pending = "pending"        # aguardando o horário / próxima tentativa
    processing = "processing"  # sendo enviada agora (lock do poller)
    sent = "sent"              # confirmada pelo WAHA
    failed = "failed"          # esgotou as tentativas
    canceled = "canceled"      # schedule cancelado antes do disparo
    skipped = "skipped"        # atrasada além de MAX_OVERDUE_MINUTES

    def __str__(self) -> str:  # facilita uso em templates
        return self.value


TERMINAL_STATUSES = {
    DispatchStatus.sent,
    DispatchStatus.failed,
    DispatchStatus.canceled,
    DispatchStatus.skipped,
}
OPEN_STATUSES = {DispatchStatus.pending, DispatchStatus.processing}


class ScheduleSource(str, enum.Enum):
    """De onde veio um agendamento (`ScheduleGroup.source`)."""

    manual = "manual"              # tela Agendamentos
    conversation = "conversation"  # tela Conversas
    calendar = "calendar"          # automação de um evento do Calendário

    def __str__(self) -> str:
        return self.value


class ScheduleGroup(SQLModel, table=True):
    """UM agendamento, do ponto de vista do usuário: um destinatário, um
    WhatsApp, um horário de início e uma SEQUÊNCIA de mensagens (`Schedule`s
    com o mesmo `group_id`, ordenados por `Schedule.position`).

    É o modelo único usado por Conversas, Agendamentos e Calendário — só
    `source` muda. O motor de envio (`scheduler.py`) continua trabalhando por
    `Schedule`/`Dispatch` e não sabe o que é um grupo; o status do grupo não é
    guardado, é derivado dos dispatches (`schedule_views.group_status`), então
    nunca fica dessincronizado do que realmente foi enviado.

    `start_local` + `timezone` é o horário que o USUÁRIO digitou (parede, no
    fuso dele) e nunca é alterado por adicionar mensagens; o horário de cada
    mensagem é `start + position * message_gap_seconds`."""

    __tablename__ = "schedule_groups"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    source: ScheduleSource = Field(default=ScheduleSource.manual, index=True)
    # Nome interno da sessão WAHA (`WhatsAppSession.session_name`) — igual ao `Schedule.session` de cada mensagem.
    session: str
    recipient_input: str
    # Nome do contato como o usuário o viu ao escolher (só exibição); vazio =
    # número digitado à mão ou agendamento antigo — aí vale `recipient_input`.
    recipient_name: str | None = None
    chat_id: str = Field(index=True)
    timezone: str
    start_local: datetime
    message_gap_seconds: int = 3
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    # Nullable: linhas criadas antes da autenticação existir ficam sem dono
    # até `db.claim_orphan_data` associá-las ao primeiro usuário cadastrado.
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    # Agendamento (`ScheduleGroup`) a que esta mensagem pertence e a posição
    # dela na sequência (0 = primeira). Nullable só por causa de linhas antigas
    # — `service.backfill_groups` agrupa tudo no boot.
    group_id: str | None = Field(default=None, foreign_key="schedule_groups.id", index=True)
    position: int = 0
    session: str = "default"
    recipient_input: str
    chat_id: str = Field(index=True)
    text: str
    timezone: str
    # Horário informado pelo usuário, naive, interpretado em `timezone`.
    first_run_local: datetime
    # None = disparo único. Caso contrário, expressão cron de 5 campos.
    recurrence: str | None = None
    enabled: bool = Field(default=True, index=True)
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Dispatch(SQLModel, table=True):
    __tablename__ = "dispatches"

    id: str = Field(default_factory=_uuid, primary_key=True)
    schedule_id: str = Field(foreign_key="schedules.id", index=True)
    scheduled_at_utc: datetime = Field(index=True)
    status: DispatchStatus = Field(default=DispatchStatus.pending, index=True)
    attempts: int = 0
    last_error: str | None = None
    waha_message_id: str | None = None
    sent_at_utc: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CachedMessage(SQLModel, table=True):
    """Cache local do histórico de conversas (o WEBJS é lento para buscar)."""

    __tablename__ = "cached_messages"

    # message_id continua sendo a PK (evita reconstruir a tabela toda num banco
    # já com dados — SQLite não faz ALTER de chave primária). Uma colisão de
    # message_id entre sessões WAHA de dois usuários diferentes é extremamente
    # improvável (o WAHA já compõe o id a partir do chat); no pior caso uma
    # linha de cache é sobrescrita, não um vazamento de dado entre contas —
    # `user_id` é o que decide o que cada usuário VÊ nas consultas.
    message_id: str = Field(primary_key=True)
    # Nullable pelo mesmo motivo de Schedule.user_id (ver bloco de usuários acima).
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    chat_id: str = Field(index=True)
    ts: int = Field(default=0, index=True)  # epoch em segundos
    from_me: bool = False
    body: str = ""
    msg_type: str = "chat"
    has_media: bool = False
    ack_name: str | None = None
    synced_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- #
# Calendários externos (Google Agenda e, futuramente, outros provedores).
#
# Tabelas 100% novas — nenhum campo é adicionado a `Schedule`/`Dispatch`
# acima. Isso é deliberado: este projeto não tem Alembic/migração, e
# `SQLModel.metadata.create_all()` só cria tabelas que ainda não existem, não
# altera tabelas já existentes num banco em produção. Ligar um evento externo
# a um `Schedule` é feito só via `EventAutomation` (uma tabela de "cola"),
# então um banco já rodando ganha as tabelas novas sozinho no próximo boot,
# sem nenhum risco para os agendamentos que já existem.
# --------------------------------------------------------------------------- #
class CalendarConnectionStatus(str, enum.Enum):
    active = "active"
    error = "error"
    disconnected = "disconnected"

    def __str__(self) -> str:
        return self.value


class EventSource(str, enum.Enum):
    internal = "internal"
    google = "google"

    def __str__(self) -> str:
        return self.value


class EventStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"

    def __str__(self) -> str:
        return self.value


class OffsetUnit(str, enum.Enum):
    minutes = "minutes"
    hours = "hours"
    days = "days"
    weeks = "weeks"

    def __str__(self) -> str:
        return self.value


class OffsetDirection(str, enum.Enum):
    before = "before"
    at = "at"
    after = "after"
    # Horário absoluto (ex.: "18:00"), não relativo ao evento — ver
    # Automation.custom_time_local. offset_amount/offset_unit são ignorados
    # nesse modo (mantidos no schema por simplicidade, não usados no cálculo).
    custom = "custom"

    def __str__(self) -> str:
        return self.value


class CalendarConnection(SQLModel, table=True):
    """Uma conta conectada num provedor de calendário (ex.: uma conta Google)."""

    __tablename__ = "calendar_connections"

    id: str = Field(default_factory=_uuid, primary_key=True)
    # Nullable pelo mesmo motivo de Schedule.user_id (ver bloco de usuários acima).
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    provider: str = Field(index=True)  # "google" | futuramente "outlook" | "apple"
    account_identifier: str = ""  # e-mail da conta, só para exibição
    # Tokens sempre cifrados (ver crypto.py) — nunca texto puro no banco.
    access_token_enc: str
    refresh_token_enc: str
    token_expires_at: datetime
    scope: str = ""
    status: CalendarConnectionStatus = Field(default=CalendarConnectionStatus.active, index=True)
    last_sync_at: datetime | None = None
    last_sync_error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Calendar(SQLModel, table=True):
    """Um calendário individual dentro de uma conta conectada (ex.: "Trabalho")."""

    __tablename__ = "calendars"
    __table_args__ = (UniqueConstraint("connection_id", "external_id", name="uq_calendar_connection_external"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    connection_id: str = Field(foreign_key="calendar_connections.id", index=True)
    external_id: str
    name: str
    # Timezone do calendário no provedor — necessário para eventos de dia
    # inteiro, que não trazem timezone própria (ex.: Google `start.date`).
    time_zone: str = "UTC"
    color: str | None = None
    enabled: bool = Field(default=False, index=True)  # usuário escolheu sincronizar
    sync_token: str | None = None  # cursor incremental do provedor
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Event(SQLModel, table=True):
    """Um evento de calendário, interno ou importado de um provedor externo."""

    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("calendar_id", "external_id", name="uq_event_calendar_external"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    # Nullable pelo mesmo motivo de Schedule.user_id (ver bloco de usuários acima).
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    source: EventSource = Field(default=EventSource.internal, index=True)
    calendar_id: str | None = Field(default=None, foreign_key="calendars.id", index=True)
    external_id: str | None = None
    # Id da série recorrente no provedor (não usado ainda; guardado para uma
    # futura opção de "aplicar automação a toda a série").
    recurring_event_id: str | None = None
    title: str = ""
    description: str = ""
    start_utc: datetime = Field(index=True)
    end_utc: datetime
    timezone: str = "UTC"
    all_day: bool = False
    status: EventStatus = Field(default=EventStatus.confirmed, index=True)
    # `updated` do provedor — permite detectar mudança sem comparar campo a campo.
    provider_updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class EventAutomation(SQLModel, table=True):
    """MODELO LEGADO (incremento 2) — 1 `Schedule` por linha, 1 mensagem só.

    Substituído pelo trio `Automation`/`AutomationMessage`/`AutomationSchedule`
    abaixo (incremento 3, várias mensagens por automação). Mantido intocado
    no schema só para a migração `calendar_service.migrate_legacy_automations`
    ler uma vez no boot e converter os dados reais já existentes — nenhum
    código novo lê ou escreve aqui depois disso.
    """

    __tablename__ = "event_automations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(foreign_key="events.id", index=True)
    schedule_id: str = Field(foreign_key="schedules.id", unique=True, index=True)
    offset_amount: int
    offset_unit: OffsetUnit
    offset_direction: OffsetDirection
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Automation(SQLModel, table=True):
    """Uma automação: N destinatários x M mensagens (`AutomationMessage`),
    uma regra de tempo única (offset), ligada a um evento."""

    __tablename__ = "automations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(foreign_key="events.id", index=True)
    offset_amount: int
    offset_unit: OffsetUnit
    offset_direction: OffsetDirection
    # Só usado quando offset_direction == custom: horário absoluto "HH:MM",
    # combinado com a data local do evento a cada (re)cálculo. Coluna
    # adicionada via ALTER TABLE em db.py (tabela pré-existente, sem
    # Alembic) — por isso precisa ser nullable.
    custom_time_local: str | None = Field(default=None)
    # "1:45" quando o usuário escolheu Intervalo = "Personalizado" (antes/depois).
    # `offset_amount`/`offset_unit` guardam o mesmo valor normalizado (105
    # minutes) e são o que o cálculo usa; este texto só existe pra o formulário
    # de edição voltar mostrando exatamente "Personalizado · 1:45". Coluna
    # adicionada via ALTER TABLE em db.py.
    custom_interval: str | None = Field(default=None)
    # Intervalo padrão entre o envio de uma mensagem e a próxima da mesma
    # automação/destinatário — arquitetura pronta para virar configurável
    # por mensagem no futuro, sem precisar mudar o schema de novo.
    message_gap_seconds: int = 3
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AutomationMessage(SQLModel, table=True):
    """Uma mensagem da sequência de uma automação. `position` define a ordem
    de envio (0 = primeira)."""

    __tablename__ = "automation_messages"

    id: str = Field(default_factory=_uuid, primary_key=True)
    automation_id: str = Field(foreign_key="automations.id", index=True)
    position: int
    text: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AutomationSchedule(SQLModel, table=True):
    """Liga uma (`AutomationMessage`, destinatário) a um `Schedule` real —
    uma linha por mensagem x destinatário. `recipient_chat_id` é uma cópia
    imutável de `Schedule.chat_id` capturada na criação, só para permitir
    agrupar/consultar sem precisar juntar com `schedules` toda vez."""

    __tablename__ = "automation_schedules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    automation_id: str = Field(foreign_key="automations.id", index=True)
    message_id: str = Field(foreign_key="automation_messages.id", index=True)
    schedule_id: str = Field(foreign_key="schedules.id", unique=True, index=True)
    recipient_chat_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)


class ScheduleDependency(SQLModel, table=True):
    """0 ou 1 linha por `Schedule` — existe só para mensagens encadeadas
    (posição > 0 de uma automação). `scheduler.py` só materializa/despacha
    `schedule_id` depois que a última `Dispatch` de `depends_on_schedule_id`
    chegar a `sent`; se a dependência terminar sem sucesso, este `Schedule`
    é desativado em vez de despachado (a cadeia aborta em vez de sair de
    ordem). Ver `scheduler._dependency_gate`. Tabela genérica, não amarrada
    a calendário/automação — o motor de envio continua sem saber o que é
    uma "automação"."""

    __tablename__ = "schedule_dependencies"

    schedule_id: str = Field(foreign_key="schedules.id", primary_key=True)
    depends_on_schedule_id: str = Field(foreign_key="schedules.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class EventSyncStatus(SQLModel, table=True):
    """Status (só de exibição) do último push de um evento interno pro
    Google Agenda. Só existe para eventos vinculados (`Event.external_id`
    setado) — nunca criada para um evento puramente interno, e nunca usada
    para travar leitura (a garantia de consistência vem de nunca commitar
    uma edição local cujo push falhou — ver `calendar_service`)."""

    __tablename__ = "event_sync_status"

    event_id: str = Field(foreign_key="events.id", primary_key=True)
    status: str = "synced"  # "synced" | "error"
    error: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class AppSetting(SQLModel, table=True):
    """Configurações do app persistidas em runtime (ex.: fuso horário
    global) — sobrepõe o valor default lido de `.env`/`Settings` sem exigir
    reiniciar o processo. Ver `app_settings.py`."""

    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- #
# Usuários, sessões e autenticação.
#
# Tabelas 100% novas, mesmo raciocínio do bloco de calendários acima: sem
# Alembic, `create_all()` só cria o que ainda não existe, então um banco já
# rodando ganha estas tabelas sozinho no próximo boot. As colunas `user_id`
# adicionadas às tabelas pré-existentes (Schedule, CalendarConnection, Event,
# CachedMessage) entram via ALTER TABLE em db.py — nullable, porque dados
# criados antes da autenticação existir não têm dono até alguém reivindicar
# (ver `db.claim_orphan_data`).
# --------------------------------------------------------------------------- #
def _waha_session_default() -> str:
    return f"u_{uuid4().hex[:12]}"


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    # Sempre normalizado (trim + lowercase) antes de salvar — ver auth.py.
    email: str = Field(index=True)
    password_hash: str
    phone: str | None = None  # telefone da CONTA — nunca o número do WhatsApp conectado
    # LEGADO (v1.2, WhatsApp único por usuário) — superseded por `WhatsAppSession`
    # (v1.3, N por usuário). Mantido só para a migração idempotente no boot
    # (`whatsapp_service.migrate_legacy_sessions`) criar a primeira
    # `WhatsAppSession` de cada usuário existente sem perder o pareamento já
    # feito. Código novo nunca lê este campo diretamente.
    waha_session: str = Field(default_factory=_waha_session_default, unique=True, index=True)
    timezone: str | None = None  # fuso pessoal do usuário; None = usa settings.default_timezone (só p/ conta nova)
    email_verified: bool = False
    is_active: bool = True
    # None = ainda não terminou (nem pulou até o fim) o onboarding de primeiros
    # passos — ver `onboarding_service.py`. Coluna aditiva (ALTER TABLE em
    # db.py); contas que já existiam antes desta versão são retroativamente
    # marcadas como concluídas numa migração de boot única, pra não forçar
    # quem já usa o app a ver a tela de onboarding do nada.
    onboarding_completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class WhatsAppSession(SQLModel, table=True):
    """Um número de WhatsApp conectado por um usuário — um usuário pode ter
    várias (v1.3, item 9). `session_name` é o nome interno da sessão no WAHA:
    gerado uma vez, nunca muda — é o mesmo valor gravado em `Schedule.session`
    e usado pelo scheduler pra disparar, então editar `name` (o rótulo de
    exibição, ex. "Trabalho") depois de criada nunca precisa tocar aqui.
    `disconnected_at` é soft-delete, mesmo padrão de `CalendarConnection`:
    histórico (`Schedule`/`Dispatch`) preservado, só some da lista de conexões
    ativas do usuário."""

    __tablename__ = "whatsapp_sessions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str = "WhatsApp"
    session_name: str = Field(default_factory=_waha_session_default, unique=True, index=True)
    engine: str | None = None
    disconnected_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BillingProfile(SQLModel, table=True):
    """Dados de cobrança — 1:1 com User, sempre opcional (nunca bloqueia o uso do app)."""

    __tablename__ = "billing_profiles"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True, index=True)
    legal_name: str = ""
    postal_code: str = ""
    address: str = ""
    number: str = ""
    complement: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class UserSession(SQLModel, table=True):
    """Sessão de login (cookie httponly). O cookie guarda o token opaco em
    texto puro; aqui só fica o hash SHA-256 dele — um vazamento do banco não
    basta para sequestrar uma sessão. Ver auth.py."""

    __tablename__ = "user_sessions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None
    revoked_at: datetime | None = None


class PasswordResetToken(SQLModel, table=True):
    """Token de recuperação de senha — mesmo padrão de UserSession: só o
    hash é persistido, o token em si só existe no link enviado ao usuário."""

    __tablename__ = "password_reset_tokens"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    used_at: datetime | None = None


class EmailVerificationToken(SQLModel, table=True):
    __tablename__ = "email_verification_tokens"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    used_at: datetime | None = None


class AuditEventType(str, enum.Enum):
    login_success = "login_success"
    login_failed = "login_failed"
    logout = "logout"
    register = "register"
    password_changed = "password_changed"
    password_reset_requested = "password_reset_requested"
    password_reset_completed = "password_reset_completed"
    email_changed = "email_changed"
    google_connected = "google_connected"
    google_disconnected = "google_disconnected"
    whatsapp_reconnected = "whatsapp_reconnected"

    def __str__(self) -> str:
        return self.value


class LoginAuditEvent(SQLModel, table=True):
    """Trilha de auditoria de segurança da conta — nunca guarda senha ou
    token, só o suficiente para investigar um incidente (Parte 38)."""

    __tablename__ = "login_audit_events"

    id: str = Field(default_factory=_uuid, primary_key=True)
    # Nulo em login_failed com e-mail que não existe (não há usuário a ligar).
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    event_type: AuditEventType = Field(index=True)
    detail: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
