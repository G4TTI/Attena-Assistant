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
