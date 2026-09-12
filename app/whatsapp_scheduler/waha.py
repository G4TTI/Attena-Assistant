"""Cliente HTTP do WAHA (https://waha.devlike.pro).

Só os endpoints que o agendador precisa: status da sessão, QR de pareamento e
envio de texto. Todo erro de rede/HTTP vira `WahaError` com mensagem legível.
"""

from __future__ import annotations

from typing import Any

import httpx


class WahaError(RuntimeError):
    """Falha ao falar com o WAHA."""


def extract_message_id(payload: Any) -> str | None:
    """O formato do id varia conforme o engine (WEBJS/NOWEB/GOWS)."""
    if not isinstance(payload, dict):
        return None
    mid = payload.get("id")
    if isinstance(mid, str):
        return mid
    if isinstance(mid, dict):
        return mid.get("_serialized") or mid.get("id")
    return None


class WahaClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0) -> None:
        headers = {"X-Api-Key": api_key} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if kwargs.get("timeout") is None:
            kwargs.pop("timeout", None)
        try:
            resp = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise WahaError(f"Falha de conexão com o WAHA: {exc}") from exc
        if resp.status_code >= 400:
            body = resp.text[:500]
            raise WahaError(f"WAHA respondeu {resp.status_code} em {method} {url}: {body}")
        return resp

    async def get_session_status(self, session: str) -> dict[str, Any]:
        resp = await self._request("GET", f"/api/sessions/{session}")
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    async def get_qr(self, session: str) -> tuple[bytes, str]:
        """Retorna (conteúdo, content-type) da imagem de QR."""
        resp = await self._request("GET", f"/api/{session}/auth/qr", params={"format": "image"})
        return resp.content, resp.headers.get("content-type", "image/png")

    async def start_session(self, session: str) -> dict[str, Any]:
        # Tenta o endpoint novo; cai para o antigo se necessário.
        try:
            resp = await self._request("POST", f"/api/sessions/{session}/start")
        except WahaError:
            resp = await self._request(
                "POST", "/api/sessions", json={"name": session, "start": True}
            )
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}

    async def restart_session(self, session: str) -> dict[str, Any]:
        """Recupera uma sessão travada (ex: status FAILED após o WhatsApp desconectar).

        Um simples `start` costuma não fazer nada numa sessão já existente em
        estado ruim — é preciso parar e iniciar de novo (ou usar o endpoint
        `/restart`, quando o WAHA o suporta) para o engine gerar um QR novo.
        """
        try:
            resp = await self._request("POST", f"/api/sessions/{session}/restart")
            data = resp.json()
            return data if isinstance(data, dict) else {"raw": data}
        except WahaError:
            pass  # WAHA mais antigo não tem /restart — cai para stop + start

        try:
            await self._request("POST", f"/api/sessions/{session}/stop")
        except WahaError:
            pass  # já parada, ou nunca existiu — segue para o start mesmo assim

        return await self.start_session(session)

    async def send_text(self, session: str, chat_id: str, text: str) -> dict[str, Any]:
        resp = await self._request(
            "POST",
            "/api/sendText",
            json={"session": session, "chatId": chat_id, "text": text},
        )
        try:
            data = resp.json()
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {"raw": data}

    async def get_chats_overview(
        self, session: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        """Lista de conversas com nome, foto e última mensagem."""
        resp = await self._request(
            "GET",
            f"/api/{session}/chats/overview",
            params={"limit": limit, "offset": 0},
            timeout=timeout,
        )
        data = resp.json()
        return data if isinstance(data, list) else []

    async def get_messages(
        self, session: str, chat_id: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        """Histórico de uma conversa (mais recentes primeiro no WAHA)."""
        resp = await self._request(
            "GET",
            f"/api/{session}/chats/{chat_id}/messages",
            params={"limit": limit, "downloadMedia": "false"},
            timeout=timeout,
        )
        data = resp.json()
        return data if isinstance(data, list) else []
