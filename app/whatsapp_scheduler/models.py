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


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: str = Field(default_factory=_uuid, primary_key=True)
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

    message_id: str = Field(primary_key=True)
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

    def __str__(self) -> str:
        return self.value


class CalendarConnection(SQLModel, table=True):
    """Uma conta conectada num provedor de calendário (ex.: uma conta Google)."""

    __tablename__ = "calendar_connections"

    id: str = Field(default_factory=_uuid, primary_key=True)
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
