from whatsapp_scheduler import app_settings
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.models import User


def test_user_timezone_uses_users_own_value_when_set():
    user = User(name="A", email="a@example.com", password_hash="x", timezone="Asia/Tokyo")
    assert app_settings.user_timezone(user) == "Asia/Tokyo"


def test_user_timezone_falls_back_to_global_default_when_unset():
    user = User(name="A", email="a@example.com", password_hash="x", timezone=None)
    assert app_settings.user_timezone(user) == settings.default_timezone


def test_user_timezone_never_leaks_between_users():
    """Regressão do bug de isolamento corrigido na v1.3: antes, o fuso de
    TODOS os usuários vinha de uma única `settings.default_timezone` mutável
    (Configurações mudava ela globalmente). Agora cada usuário tem o seu."""
    user_a = User(name="A", email="a@example.com", password_hash="x", timezone="America/Sao_Paulo")
    user_b = User(name="B", email="b@example.com", password_hash="x", timezone="Europe/Lisbon")
    assert app_settings.user_timezone(user_a) == "America/Sao_Paulo"
    assert app_settings.user_timezone(user_b) == "Europe/Lisbon"
    # Mudar um objeto não afeta o outro nem o fallback global.
    user_a.timezone = "UTC"
    assert app_settings.user_timezone(user_a) == "UTC"
    assert app_settings.user_timezone(user_b) == "Europe/Lisbon"


# --- IP do cliente atrás de proxy/túnel (rate limit por IP) ----------------- #
def _fake_request(headers: dict[str, str], host: str = "172.18.0.1"):
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    # Headers do Starlette (case-insensitive), como no request real.
    return SimpleNamespace(headers=Headers(headers), client=SimpleNamespace(host=host))


def test_client_ip_ignores_forwarded_headers_by_default(monkeypatch):
    from whatsapp_scheduler import auth
    from whatsapp_scheduler.config import settings

    monkeypatch.setattr(settings, "client_ip_header", "")
    assert auth.client_ip(_fake_request({"cf-connecting-ip": "1.2.3.4"})) == "172.18.0.1"


def test_client_ip_uses_configured_proxy_header(monkeypatch):
    from whatsapp_scheduler import auth
    from whatsapp_scheduler.config import settings

    monkeypatch.setattr(settings, "client_ip_header", "CF-Connecting-IP")
    assert auth.client_ip(_fake_request({"cf-connecting-ip": "203.0.113.9"})) == "203.0.113.9"
    # sem o header (acesso direto), cai pro IP da conexão
    assert auth.client_ip(_fake_request({})) == "172.18.0.1"


def test_client_ip_takes_first_hop_of_x_forwarded_for(monkeypatch):
    from whatsapp_scheduler import auth
    from whatsapp_scheduler.config import settings

    monkeypatch.setattr(settings, "client_ip_header", "X-Forwarded-For")
    assert auth.client_ip(_fake_request({"x-forwarded-for": "198.51.100.7, 10.0.0.2"})) == "198.51.100.7"
