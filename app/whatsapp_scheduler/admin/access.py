"""Quem pode administrar e como esse poder é concedido.

- A CONTA PRINCIPAL (`role="owner"`, e-mail em ADMIN_OWNER_EMAIL) é única e só é
  criada/redefinida pelo CLI no servidor (`cli setup-owner`).
- Ser administrador = ter o plano interno "Administrador". Só a conta principal
  atribui ou remove esse plano (e portanto o acesso ao /admin e ao CRM).
- A conta principal pode atribuir QUALQUER plano (inclusive ocultos/inativos) a
  qualquer usuário. Um administrador comum só muda o plano de usuários comuns.
- Ninguém altera o plano da conta principal nem a suspende pelo painel.
"""

from __future__ import annotations

from sqlmodel import Session

from .. import plans
from ..billing import service as billing
from ..errors import ValidationError
from ..models import ADMIN_ROLES, ROLE_ADMIN, ROLE_OWNER, ROLE_USER, Plan, User


def is_owner(user: User | None) -> bool:
    return user is not None and user.role == ROLE_OWNER


def is_admin(user: User | None) -> bool:
    return user is not None and user.role in ADMIN_ROLES


def assignable_plans(db: Session, actor: User) -> list[Plan]:
    """Planos que `actor` pode escolher no painel: a conta principal vê todos
    (inclusive "Administrador" e os ocultos/inativos); os demais admins, todos
    menos o "Administrador"."""
    catalog = plans.list_plans(db)
    return catalog if is_owner(actor) else [p for p in catalog if not plans.is_admin_plan(p)]


def can_manage(actor: User, target: User) -> bool:
    """`actor` pode mudar plano/suspender `target`? A conta principal nunca é
    alvo; outros admins só são alvo da conta principal."""
    if target.role == ROLE_OWNER:
        return False
    if target.role == ROLE_ADMIN:
        return is_owner(actor)
    return is_admin(actor)


def set_plan(db: Session, actor: User, target: User, plan: Plan) -> tuple[str | None, str | None]:
    """Atribui `plan` a `target` (cortesia, nunca receita). Devolve (código do
    plano anterior, "granted" | "revoked" | None para o acesso de admin)."""
    if target.role == ROLE_OWNER:
        raise ValidationError("O plano da conta principal não pode ser alterado.")
    if (plans.is_admin_plan(plan) or target.role == ROLE_ADMIN) and not is_owner(actor):
        raise ValidationError("Só a conta principal pode conceder ou remover o acesso de administrador.")
    if not is_admin(actor):
        raise ValidationError("Sem permissão.")
    previous = plans.current_plan(db, target)
    billing.grant_plan_manually(db, target, plan)
    change = None
    if plans.is_admin_plan(plan) and target.role != ROLE_ADMIN:
        target.role, change = ROLE_ADMIN, "granted"
    elif not plans.is_admin_plan(plan) and target.role == ROLE_ADMIN:
        target.role, change = ROLE_USER, "revoked"
    db.add(target)
    db.commit()
    return (previous.code if previous else None), change


def revoke_admin(db: Session, target: User) -> bool:
    """Tira o acesso de admin (volta ao plano padrão). Usado pelo CLI de
    emergência e ao (re)definir a conta principal. Nunca rebaixa a principal."""
    if target.role != ROLE_ADMIN:
        return False
    current = plans.current_plan(db, target)
    if plans.is_admin_plan(current):
        default = plans.default_plan(db)
        if default is not None:
            billing.grant_plan_manually(db, target, default)
    target.role = ROLE_USER
    db.add(target)
    db.commit()
    return True
