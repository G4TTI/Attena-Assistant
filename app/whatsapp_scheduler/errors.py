"""Erros de domínio compartilhados (ficam aqui pra `timing.py`, `service.py` e
o resto poderem levantá-los sem import circular)."""

from __future__ import annotations


class ValidationError(ValueError):
    """Dado de entrada inválido (vira HTTP 422 na API e mensagem no formulário na UI)."""
