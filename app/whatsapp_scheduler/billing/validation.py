"""Validação dos "Dados para faturamento" (pedidos só no upgrade)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import phonenumbers

from ..errors import ValidationError

UF_NAMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

_NON_DIGIT = re.compile(r"\D")


def digits(value: str | None) -> str:
    return _NON_DIGIT.sub("", value or "")


def is_valid_cpf(value: str | None) -> bool:
    """Formato + dígitos verificadores (módulo 11). Rejeita sequências repetidas."""
    cpf = digits(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[i]) * (size + 1 - i) for i in range(size))
        check = (total * 10) % 11 % 10
        if check != int(cpf[size]):
            return False
    return True


def format_cpf(value: str) -> str:
    cpf = digits(value)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def mask_cpf(last2: str | None) -> str:
    return f"***.***.***-{last2}" if last2 else "—"


def format_cep(value: str) -> str:
    cep = digits(value)
    return f"{cep[:5]}-{cep[5:]}"


def normalize_phone(value: str | None) -> str:
    raw = (value or "").strip()
    try:
        parsed = phonenumbers.parse(raw, None if raw.startswith("+") else "BR")
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Telefone inválido. Use DDD + número, ex.: (11) 99999-8888.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError("Telefone inválido. Use DDD + número, ex.: (11) 99999-8888.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@dataclass
class BillingForm:
    full_name: str
    cpf: str | None  # None = manter o CPF já salvo
    phone: str
    postal_code: str
    address: str
    address_number: str
    address_complement: str
    city: str
    state: str


def _required(value: str, label: str, max_len: int) -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"Informe {label}.")
    if len(value) > max_len:
        raise ValidationError(f"{label[0].upper() + label[1:]} pode ter no máximo {max_len} caracteres.")
    return value


def validate_form(data: dict[str, str], *, has_saved_cpf: bool) -> BillingForm:
    full_name = _required(data.get("full_name", ""), "o nome completo", 160)
    if len(full_name.split()) < 2:
        raise ValidationError("Informe o nome completo (nome e sobrenome).")
    cpf_raw = (data.get("cpf") or "").strip()
    if cpf_raw:
        if not is_valid_cpf(cpf_raw):
            raise ValidationError("CPF inválido. Confira os 11 dígitos.")
        cpf = digits(cpf_raw)
    elif has_saved_cpf:
        cpf = None
    else:
        raise ValidationError("Informe o CPF.")
    phone = normalize_phone(_required(data.get("phone", ""), "o telefone", 30))
    cep = digits(_required(data.get("postal_code", ""), "o CEP", 12))
    if len(cep) != 8:
        raise ValidationError("CEP inválido. Use 8 dígitos, ex.: 01310-100.")
    state = (data.get("state") or "").strip().upper()
    if state not in UF_NAMES:
        raise ValidationError("Selecione um estado (UF) válido.")
    complement = (data.get("address_complement") or "").strip()
    if len(complement) > 80:
        raise ValidationError("O complemento pode ter no máximo 80 caracteres.")
    return BillingForm(
        full_name=full_name,
        cpf=cpf,
        phone=phone,
        postal_code=cep,
        address=_required(data.get("address", ""), "o endereço", 160),
        address_number=_required(data.get("address_number", ""), "o número", 20),
        address_complement=complement,
        city=_required(data.get("city", ""), "a cidade", 80),
        state=state,
    )
