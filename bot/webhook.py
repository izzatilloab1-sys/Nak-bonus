"""Payme Merchant API webhook serveri (aiohttp).

Payme Merchant kabinetidagi endpoint shu serverga JSON-RPC so'rovlar yuboradi:
    https://sizning-domen.uz{PAYME_ENDPOINT_PATH}

Bu modul ikki xil ishlatilishi mumkin:
  1. Bot bilan BIR process'da (main.py chaqiradi) — tavsiya etiladi.
  2. Alohida:  python -m bot.webhook
"""
from __future__ import annotations

import json
import logging

from aiohttp import web

from bot.config import config
from bot.services import click as click_service
from bot.services import payme as payme_service
from bot.services.payme import (
    ERR_AUTH,
    ERR_INVALID_JSON,
    PaymeMerchant,
    check_auth,
)

logger = logging.getLogger("payme.webhook")

_merchant = PaymeMerchant()


def _error_response(rpc_id, code: int, message: str) -> web.Response:
    return web.json_response(
        {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": code,
                "message": {"uz": message, "ru": message, "en": message},
            },
        }
    )


async def payme_handler(request: web.Request) -> web.Response:
    """Payme JSON-RPC so'rovini qabul qiladi."""
    # 1. Basic Auth
    auth = request.headers.get("Authorization")
    if not await check_auth(auth):
        logger.warning("Payme: avtorizatsiya rad etildi")
        return _error_response(None, ERR_AUTH, "Avtorizatsiya yetarli emas")

    # 2. JSON'ni o'qiymiz
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return _error_response(None, ERR_INVALID_JSON, "JSON o'qib bo'lmadi")

    rpc_id = payload.get("id")
    logger.info("Payme so'rov: method=%s id=%s", payload.get("method"), rpc_id)

    # 3. Metodni bajaramiz
    try:
        result = await _merchant.handle(payload)
    except Exception as e:  # kutilmagan xato
        logger.exception("Payme handler xatosi: %s", e)
        return _error_response(rpc_id, -32400, "Ichki xatolik")

    return web.json_response(result)


async def click_handler(request: web.Request) -> web.Response:
    """Click SHOP API callback (Prepare / Complete). Form-urlencoded yoki JSON."""
    try:
        if request.content_type and "json" in request.content_type:
            data = await request.json()
        else:
            form = await request.post()
            data = {k: v for k, v in form.items()}
    except Exception:
        return web.json_response(
            {"error": -8, "error_note": "Bad request"}
        )

    logger.info(
        "Click callback: action=%s order=%s",
        data.get("action"),
        data.get("merchant_trans_id"),
    )
    # To'lov o'tganda foydalanuvchiga xabar beradigan notifier (payme bilan umumiy)
    notifier = payme_service.get_bot_notifier()
    try:
        result = await click_service.handle_callback(data, notifier)
    except Exception as e:
        logger.exception("Click handler xatosi: %s", e)
        return web.json_response({"error": -8, "error_note": "Internal error"})
    return web.json_response(result)


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post(config.payme_endpoint_path, payme_handler)
    app.router.add_post("/click", click_handler)
    app.router.add_get("/health", health_handler)
    return app


def run_standalone() -> None:
    logging.basicConfig(level=logging.INFO)
    app = build_app()
    web.run_app(app, host=config.webhook_host, port=config.webhook_port)


if __name__ == "__main__":
    run_standalone()
