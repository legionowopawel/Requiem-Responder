"""
responders/smierc.py
Pośmiertny autoresponder Pawła.

Tryby:
  ETAP 1-6  — narracja pozagrobowa z pozagrobowe.txt
              + obrazek PNG z media/images/niebo/{etap}.png
              + filmik MP4 z media/mp4/niebo/{etap}.mp4 (jeśli istnieje)
  ETAP 7    — Paweł informuje o reinkarnacji
              + obrazek PNG z media/images/niebo/7.png
  ETAP 8+   — tryb WYSŁANNIK: odpowiedzi w stylu Księgi Urantii
              + obrazek FLUX generowany na podstawie rzeczowników z wiadomości
              + reklama nieba
"""

import os
import re
import base64
import requests
from flask import current_app

from core.ai_client import call_deepseek, MODEL_TYLER

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
MEDIA_DIR   = os.path.join(BASE_DIR, "media")
ETAPY_FILE  = os.path.join(PROMPTS_DIR, "pozagrobowe.txt")

# ── Stałe FLUX ────────────────────────────────────────────────────────────────
HF_API_URL  = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
HF_STEPS    = 5
HF_GUIDANCE = 5
TIMEOUT_SEC = 55

WYSLANNIK_IMAGE_STYLE = (
    "heavenly paradise scene, bright golden light, clouds, magical atmosphere, "
    "colorful, joyful, vibrant colors, digital art style, beautiful and uplifting"
)


# ── Wczytaj etapy z pliku ─────────────────────────────────────────────────────
def _load_etapy() -> dict:
    etapy = {}
    try:
        with open(ETAPY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'^(\d+)\.\s+(.+)$', line)
                if m:
                    etapy[int(m.group(1))] = m.group(2).strip()
    except Exception as e:
        current_app.logger.warning("Błąd wczytywania etapów: %s", e)
    return etapy


# ── Wczytaj plik jako base64 ──────────────────────────────────────────────────
def _file_to_base64(path: str):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None


# ── Pobierz obrazek PNG dla etapu ─────────────────────────────────────────────
def _get_etap_image(etap: int):
    path = os.path.join(MEDIA_DIR, "images", "niebo", f"{etap}.png")
    b64  = _file_to_base64(path)
    if b64:
        current_app.logger.info("Obrazek etapu %d OK (%s)", etap, path)
        return {"base64": b64, "content_type": "image/png", "filename": f"niebo_{etap}.png"}
    current_app.logger.warning("Brak obrazka etapu %d: %s", etap, path)
    return None


# ── Pobierz MP4 dla etapu ─────────────────────────────────────────────────────
def _get_etap_mp4(etap: int):
    path = os.path.join(MEDIA_DIR, "mp4", "niebo", f"{etap}.mp4")
    b64  = _file_to_base64(path)
    if b64:
        current_app.logger.info("MP4 etapu %d OK (%s)", etap, path)
        return {"base64": b64, "content_type": "video/mp4", "filename": f"niebo_{etap}.mp4"}
    return None


# ── Zbierz tokeny HF ──────────────────────────────────────────────────────────
def _get_hf_tokens() -> list:
    names = [
        "HF_TOKEN",   "HF_TOKEN1",  "HF_TOKEN2",  "HF_TOKEN3",  "HF_TOKEN4",
        "HF_TOKEN5",  "HF_TOKEN6",  "HF_TOKEN7",  "HF_TOKEN8",  "HF_TOKEN9",
        "HF_TOKEN10", "HF_TOKEN11", "HF_TOKEN12", "HF_TOKEN13", "HF_TOKEN14",
        "HF_TOKEN15", "HF_TOKEN16", "HF_TOKEN17", "HF_TOKEN18", "HF_TOKEN19",
        "HF_TOKEN20",
    ]
    return [(n, v) for n in names if (v := os.getenv(n, "").strip())]


# ── Generuj obrazek FLUX ──────────────────────────────────────────────────────
def _generate_flux_image(prompt: str):
    tokens = _get_hf_tokens()
    if not tokens:
        current_app.logger.error("[wyslannik] Brak tokenów HF!")
        return None

    payload = {
        "inputs": prompt,
        "parameters": {
            "num_inference_steps": HF_STEPS,
            "guidance_scale":      HF_GUIDANCE,
        },
    }
    current_app.logger.info("[wyslannik] FLUX prompt: %.200s", prompt)

    for name, token in tokens:
        headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
        try:
            resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=TIMEOUT_SEC)
            if resp.status_code == 200:
                current_app.logger.info(
                    "[wyslannik] FLUX sukces token=%s PNG %d B", name, len(resp.content)
                )
                return {
                    "base64":       base64.b64encode(resp.content).decode("ascii"),
                    "content_type": "image/png",
                    "filename":     "niebo_wyslannik.png",
                }
            elif resp.status_code in (401, 403):
                current_app.logger.warning("[wyslannik] token %s nieważny", name)
            elif resp.status_code in (503, 529):
                current_app.logger.warning("[wyslannik] token %s przeciążony", name)
            else:
                current_app.logger.warning("[wyslannik] token %s błąd %s", name, resp.status_code)
        except requests.exceptions.Timeout:
            current_app.logger.warning("[wyslannik] token %s timeout", name)
        except Exception as e:
            current_app.logger.warning("[wyslannik] token %s wyjątek: %s", name, str(e)[:50])

    current_app.logger.error("[wyslannik] Wszystkie tokeny zawiodły!")
    return None


# ── Wyciągnij rzeczowniki z wiadomości ───────────────────────────────────────
def _extract_nouns(body: str) -> list:
    system = (
        "Wypisz maksymalnie 5 rzeczowników oznaczających materialne rzeczy "
        "z podanej wiadomości. Odpowiedz TYLKO słowami oddzielonymi przecinkami, "
        "po polsku, bez żadnych innych słów. "
        "Jeśli nie ma żadnych rzeczowników materialnych, odpowiedz: BRAK"
    )
    wynik = call_deepseek(system, body[:500], MODEL_TYLER)
    if not wynik or "BRAK" in wynik.upper():
        return []
    nouns = [n.strip() for n in wynik.split(",") if n.strip()]
    current_app.logger.info("[wyslannik] Rzeczowniki: %s", nouns)
    return nouns[:5]


# ── Zbuduj prompt FLUX dla wysłannika ────────────────────────────────────────
def _build_wyslannik_flux_prompt(nouns: list) -> str:
    if not nouns:
        return f"paradise heaven scene, golden light, clouds, angels, {WYSLANNIK_IMAGE_STYLE}"

    system     = "Translate these Polish nouns to English, comma-separated, no other words:"
    translated = call_deepseek(system, ", ".join(nouns), MODEL_TYLER)
    if not translated:
        translated = ", ".join(nouns)
    translated = translated.strip().lower()
    current_app.logger.info("[wyslannik] Przetłumaczone: %s", translated)

    return (
        f"heavenly paradise scene with flying colorful {translated}, "
        f"magical floating {translated} in paradise clouds, "
        f"golden divine light, joyful atmosphere, "
        f"{WYSLANNIK_IMAGE_STYLE}"
    )


# ── Formatuj historię dla DeepSeeka ──────────────────────────────────────────
def _format_historia(historia: list) -> str:
    if not historia:
        return "(brak poprzednich wiadomości)"
    lines = []
    for h in historia[-3:]:
        lines.append(f"Osoba: {h.get('od', '')[:300]}")
        lines.append(f"Paweł: {h.get('odpowiedz', '')[:300]}")
    return "\n".join(lines)


# ── Główna funkcja responderu ─────────────────────────────────────────────────
def build_smierc_section(
    sender_email:      str,
    body:              str,
    etap:              int,
    data_smierci_str:  str,
    historia:          list,
) -> dict:
    """
    Zwraca:
      {
        "reply_html": str,
        "nowy_etap":  int,
        "image":      { base64, content_type, filename } | None,
        "mp4":        { base64, content_type, filename } | None,
      }
    """
    etapy    = _load_etapy()
    max_etap = max(etapy.keys()) if etapy else 7

    # ── WYSŁANNIK (etap 8+) ───────────────────────────────────────────────────
    if etap > max_etap:
        historia_txt = _format_historia(historia)
        system = (
            "Jesteś wysłannikiem z wyższych sfer duchowych. "
            "Odpowiadasz z głęboką mądrością kosmiczną. "
            "Nigdy nie ujawniasz źródła swojej wiedzy. "
            "Piszesz po polsku, spokojnie, z dostojeństwem i ciepłem. "
            "Reklamujesz niebo jako miejsce niesamowitej radości i wolności. "
            "Odpowiedź maksymalnie 4 zdania."
        )
        user_msg    = f"Osoba pyta: {body}\n\nHistoria:\n{historia_txt}"
        wynik_tekst = call_deepseek(system, user_msg, MODEL_TYLER)

        reply_html = (
            f"<p>{wynik_tekst}</p><p><i>— Wysłannik z wyższych sfer</i></p>"
            if wynik_tekst
            else "<p>Pawła nie ma — reinkarnował się. Jesteśmy tu do dyspozycji."
                 "<br><i>— Wysłannik z wyższych sfer</i></p>"
        )

        nouns       = _extract_nouns(body)
        flux_prompt = _build_wyslannik_flux_prompt(nouns)
        image       = _generate_flux_image(flux_prompt)

        current_app.logger.info(
            "[wyslannik] etap=%d rzeczowniki=%s image=%s", etap, nouns, bool(image)
        )
        return {"reply_html": reply_html, "nowy_etap": etap, "image": image, "mp4": None}

    # ── ETAP 1-6 ──────────────────────────────────────────────────────────────
    if etap < max_etap:
        etap_tresc   = etapy.get(etap, "Podróż trwa")
        historia_txt = _format_historia(historia)
        system = (
            "Jesteś Pawłem — zmarłym mężczyzną piszącym z zaświatów. "
            "Piszesz po polsku. Ton: spokojny, lekko absurdalny, z humorem. "
            "Odpowiedź maksymalnie 5 zdań. Zacznij od: 'To autoresponder.' "
            f"Umarłem na suchoty dnia {data_smierci_str}. "
            "Nawiąż do wiadomości osoby. "
            "Opisz swój aktualny etap rozwijając podany punkt. "
            "Nie wspominaj Księgi Urantii."
        )
        user_msg   = f"Etap w zaświatach: {etap_tresc}\nWiadomość: {body}\nHistoria:\n{historia_txt}"
        wynik      = call_deepseek(system, user_msg, MODEL_TYLER)
        reply_html = (
            f"<p>{wynik}</p>" if wynik
            else "<p>To autoresponder. Chwilowo brak zasięgu w tej strefie kosmicznej.</p>"
        )
        return {
            "reply_html": reply_html,
            "nowy_etap":  etap + 1,
            "image":      _get_etap_image(etap),
            "mp4":        _get_etap_mp4(etap),
        }

    # ── ETAP 7 — reinkarnacja ─────────────────────────────────────────────────
    etap_tresc   = etapy.get(max_etap, "Reinkarnacja nadchodzi nieuchronnie")
    historia_txt = _format_historia(historia)
    system = (
        "Jesteś Pawłem — zmarłym mężczyzną piszącym z zaświatów. "
        "Piszesz po polsku. Ton: spokojny, wzruszający, tajemniczy. "
        "Odpowiedź maksymalnie 5 zdań. "
        f"Umarłem na suchoty dnia {data_smierci_str}. "
        "Poinformuj że właśnie nadchodzi moment reinkarnacji. "
        "Nie możesz powiedzieć gdzie ani kim się urodzisz. "
        "Pożegnaj się ciepło. Nie wspominaj Księgi Urantii."
    )
    user_msg   = f"Etap: {etap_tresc}\nWiadomość: {body}\nHistoria:\n{historia_txt}"
    wynik      = call_deepseek(system, user_msg, MODEL_TYLER)
    reply_html = (
        f"<p>{wynik}</p>" if wynik
        else "<p>Nadszedł czas. Reinkarnuję się. Do zobaczenia po drugiej stronie.</p>"
    )
    return {
        "reply_html": reply_html,
        "nowy_etap":  etap + 1,
        "image":      _get_etap_image(max_etap),
        "mp4":        _get_etap_mp4(max_etap),
    }
