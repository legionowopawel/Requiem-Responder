#!/usr/bin/env python3
"""
app_smierc.py
Osobny backend Flask dla pośmiertnego autorespondera Pawła.

Endpoint: POST /webhook_smierc
Oczekiwany JSON:
  {
    "sender":          "ania@gmail.com",
    "body":            "żyjesz?",
    "etap":            1,
    "data_smierci":    "dwudziestego szóstego lutego dwa tysiące dwudziestego szóstego roku",
    "historia":        [{"od": "...", "odpowiedz": "..."}, ...]
  }

Odpowiedź:
  {
    "reply_html": "...",
    "nowy_etap":  2
  }
"""

import os
from flask import Flask, request, jsonify
from responders.smierc import build_smierc_section

app = Flask(__name__)


@app.route("/webhook_smierc", methods=["POST"])
def webhook_smierc():
    data = request.json or {}

    sender         = data.get("sender",         "")
    body           = data.get("body",           "")[:2000]
    etap           = int(data.get("etap",       1))
    data_smierci   = data.get("data_smierci",   "nieznanego dnia")
    historia       = data.get("historia",       [])

    if not body:
        return jsonify({"error": "Brak treści wiadomości"}), 400

    app.logger.info(
        "webhook_smierc — sender=%s | etap=%d | historia=%d wpisów",
        sender, etap, len(historia)
    )

    wynik = build_smierc_section(
        sender_email     = sender,
        body             = body,
        etap             = etap,
        data_smierci_str = data_smierci,
        historia         = historia,
    )

    app.logger.info(
        "webhook_smierc — odpowiedź: nowy_etap=%d | html=%d znaków",
        wynik.get("nowy_etap", etap),
        len(wynik.get("reply_html", ""))
    )

    return jsonify(wynik), 200


@app.route("/", methods=["GET"])
def index():
    return "Pośmiertny autoresponder Pawła — działa.", 200


if __name__ == "__main__":
    if not os.getenv("API_KEY_DEEPSEEK"):
        app.logger.warning("Brak API_KEY_DEEPSEEK!")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
