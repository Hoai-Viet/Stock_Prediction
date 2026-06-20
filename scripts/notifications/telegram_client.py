import requests


def send_telegram_message(bot_token, chat_id, message, timeout=30):
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")

    result = payload.get("result", {})
    return result.get("message_id")
