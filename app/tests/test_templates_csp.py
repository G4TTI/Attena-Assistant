"""O app manda `Content-Security-Policy: script-src 'self' https://unpkg.com 'unsafe-inline'`
(sem 'unsafe-eval'). O htmx avalia filtros de trigger (`hx-trigger="every 3s [expr]"`)
com eval, então o navegador os bloqueia — e o htmx trata o filtro como verdadeiro em
silêncio. Foi assim que o polling "que pausa enquanto digita" nunca pausou de verdade."""

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "whatsapp_scheduler" / "web" / "templates"


def test_no_template_uses_an_htmx_trigger_filter_that_needs_eval():
    offenders = []
    for path in sorted(TEMPLATES.glob("*.html")):
        for match in re.finditer(r'hx-trigger="([^"]*)"', path.read_text(encoding="utf-8")):
            if "[" in match.group(1):
                offenders.append(f"{path.name}: {match.group(1)}")
    assert not offenders, (
        "Filtro [expr] em hx-trigger exige eval e a CSP o bloqueia (o filtro é ignorado). "
        "Use data-pause-on-input + o listener de base.html. Encontrado: " + "; ".join(offenders)
    )


def test_pollers_that_contain_inputs_opt_into_pause_on_input():
    for name in ("_whatsapp_list.html", "_onboarding_whatsapp_step.html"):
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        assert "data-pause-on-input" in text, name
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "htmx:beforeRequest" in base and "data-pause-on-input" in base


def test_base_refreshes_preserved_qr_images_without_recreating_them():
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "refreshQrImages" in base and "img[data-qr-src]" in base
    # blob: não é permitido pela CSP (img-src 'self' data: https:) — tem de ser data: URL.
    assert "readAsDataURL" in base and "createObjectURL" not in base


def test_base_loads_new_qr_images_when_htmx_adds_them():
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "loadNewQrImages" in base and "htmx:load" in base
    assert "img[data-qr-src]:not([src])" in base
