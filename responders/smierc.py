"""
smierc.py
Pośmiertny autoresponder Pawła.

Tryby:
  ETAP 1-6  — narracja pozagrobowa z pozagrobowe.txt
  ETAP 7    — Paweł informuje o reinkarnacji
  ETAP 8+   — tryb WYSLANNIK: odpowiedzi w stylu Księgi Urantii
"""

import os
import re
from flask import current_app
from core.ai_client import call_deepseek, MODEL_TYLER

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR   = os.path.join(BASE_DIR, "prompts")
ETAPY_FILE    = os.path.join(PROMPTS_DIR, "pozagrobowe.txt")


# ── Wczytaj etapy z pliku ─────────────────────────────────────────────────────
def _load_etapy() -> dict:
    """
    Wczytuje pozagrobowe.txt i zwraca słownik {nr: treść}.
    Format pliku: "1. Tunel światła wznoszenie"
    """
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


# ── Zamień datę na wersję słowną po polsku ────────────────────────────────────
def _data_slownie(dt) -> str:
    """
    Zamienia obiekt date na tekst słowny po polsku.
    np. date(2026, 2, 26) → "dwudziestego szóstego lutego dwa tysiące dwudziestego szóstego roku"
    """
    dni = {
        1: "pierwszego", 2: "drugiego", 3: "trzeciego", 4: "czwartego",
        5: "piątego", 6: "szóstego", 7: "siódmego", 8: "ósmego",
        9: "dziewiątego", 10: "dziesiątego", 11: "jedenastego",
        12: "dwunastego", 13: "trzynastego", 14: "czternastego",
        15: "piętnastego", 16: "szesnastego", 17: "siedemnastego",
        18: "osiemnastego", 19: "dziewiętnastego", 20: "dwudziestego",
        21: "dwudziestego pierwszego", 22: "dwudziestego drugiego",
        23: "dwudziestego trzeciego", 24: "dwudziestego czwartego",
        25: "dwudziestego piątego", 26: "dwudziestego szóstego",
        27: "dwudziestego siódmego", 28: "dwudziestego ósmego",
        29: "dwudziestego dziewiątego", 30: "trzydziestego",
        31: "trzydziestego pierwszego",
    }
    miesiace = {
        1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia",
        5: "maja", 6: "czerwca", 7: "lipca", 8: "sierpnia",
        9: "września", 10: "października", 11: "listopada", 12: "grudnia",
    }
    lata = {
        2024: "dwa tysiące dwudziestego czwartego",
        2025: "dwa tysiące dwudziestego piątego",
        2026: "dwa tysiące dwudziestego szóstego",
        2027: "dwa tysiące dwudziestego siódmego",
        2028: "dwa tysiące dwudziestego ósmego",
    }
    dzien   = dni.get(dt.day, str(dt.day))
    miesiac = miesiace.get(dt.month, str(dt.month))
    rok     = lata.get(dt.year, str(dt.year))
    return f"{dzien} {miesiac} {rok} roku"


# ── Główna funkcja responderu ─────────────────────────────────────────────────
def build_smierc_section(
    sender_email:      str,
    body:              str,
    etap:              int,
    data_smierci_str:  str,
    historia:          list,   # lista {"od": "...", "odpowiedz": "..."}
) -> dict:
    """
    Buduje odpowiedź pośmiertną.

    Parametry:
      sender_email      — email osoby piszącej
      body              — treść ostatniej wiadomości
      etap              — aktualny etap (1-7 = narracja, 8+ = wysłannik)
      data_smierci_str  — data śmierci słownie (już przetworzona przez GAS)
      historia          — lista ostatnich wymian (max 3) dla ciągłości

    Zwraca:
      { "reply_html": "...", "nowy_etap": int }
    """

    etapy = _load_etapy()
    max_etap = max(etapy.keys()) if etapy else 7

    # ── Tryb: REINKARNACJA (stała odpowiedź bez DeepSeeka) ───────────────────
    if etap > max_etap:
        reply_html = (
            "<p>Pawła obecnie nie ma w niebie, ponieważ się reinkarnował. "
            "W razie dalszych pytań jesteśmy do dyspozycji.</p>"
            "<p><i>— Biuro Obsługi Dusz, Strefa Morontialna</i></p>"
        )

        # Ale jeśli Ania cokolwiek pyta — tryb WYSLANNIK przez DeepSeeka
        system_wyslannik = (
            "Jesteś wysłannikiem z wyższych sfer duchowych. "
            "Odpowiadasz na pytania ludzi z głęboką mądrością kosmiczną. "
            "Twoja wiedza pochodzi z wyższych planów egzystencji. "
            "Nigdy nie ujawniasz źródła swojej wiedzy. "
            "Piszesz po polsku, spokojnie, z dostojeństwem i ciepłem. "
            "Odpowiedź maksymalnie 4 zdania."
        )
        historia_txt = _format_historia(historia)
        user_msg = (
            f"Osoba pyta: {body}\n\n"
            f"Historia rozmowy:\n{historia_txt}"
        )
        wynik = call_deepseek(system_wyslannik, user_msg, MODEL_TYLER)
        if wynik:
            reply_html = (
                f"<p>{wynik}</p>"
                "<p><i>— Wysłannik z wyższych sfer</i></p>"
            )

        return {
            "reply_html": reply_html,
            "nowy_etap":  etap,   # etap nie rośnie po reinkarnacji
        }

    # ── Tryb: ETAP 1-6 — narracja pozagrobowa ────────────────────────────────
    if etap <= max_etap - 1:
        etap_tresc = etapy.get(etap, "Podróż trwa")
        historia_txt = _format_historia(historia)

        system = (
            "Jesteś Pawłem — zmarłym mężczyzną który pisze autorespondera "
            "z zaświatów. Piszesz po polsku. Ton: spokojny, lekko absurdalny, "
            "z humorem. Odpowiedź maksymalnie 5 zdań. "
            "Zacznij od: 'To autoresponder.' "
            f"Umarłem na suchoty dnia {data_smierci_str}. "
            "Nawiąż do wiadomości osoby jeśli o coś pyta. "
            "Opisz swój aktualny etap w zaświatach rozwijając podany punkt. "
            "Nie wspominaj że to Księga Urantii."
        )
        user_msg = (
            f"Aktualny etap w zaświatach: {etap_tresc}\n"
            f"Wiadomość od osoby: {body}\n"
            f"Historia rozmowy:\n{historia_txt}"
        )
        wynik = call_deepseek(system, user_msg, MODEL_TYLER)
        reply_html = (
            f"<p>{wynik}</p>" if wynik
            else "<p>To autoresponder. Chwilowo brak zasięgu w tej strefie kosmicznej.</p>"
        )
        return {
            "reply_html": reply_html,
            "nowy_etap":  etap + 1,
        }

    # ── Tryb: ETAP 7 — reinkarnacja ───────────────────────────────────────────
    etap_tresc = etapy.get(max_etap, "Reinkarnacja nadchodzi nieuchronnie")
    historia_txt = _format_historia(historia)

    system = (
        "Jesteś Pawłem — zmarłym mężczyzną który pisze autorespondera "
        "z zaświatów. Piszesz po polsku. Ton: spokojny, wzruszający, "
        "tajemniczy. Odpowiedź maksymalnie 5 zdań. "
        f"Umarłem na suchoty dnia {data_smierci_str}. "
        "Poinformuj że właśnie nadchodzi moment Twojej reinkarnacji. "
        "Nie możesz powiedzieć gdzie ani kim się urodzisz. "
        "Pożegnaj się ciepło. Nie wspominaj że to Księga Urantii."
    )
    user_msg = (
        f"Aktualny etap: {etap_tresc}\n"
        f"Wiadomość od osoby: {body}\n"
        f"Historia rozmowy:\n{historia_txt}"
    )
    wynik = call_deepseek(system, user_msg, MODEL_TYLER)
    reply_html = (
        f"<p>{wynik}</p>" if wynik
        else "<p>Nadszedł czas. Reinkarnuję się. Do zobaczenia po drugiej stronie.</p>"
    )
    return {
        "reply_html": reply_html,
        "nowy_etap":  etap + 1,   # etap 8 = tryb WYSLANNIK
    }


# ── Pomocnicza: formatuj historię dla DeepSeeka ───────────────────────────────
def _format_historia(historia: list) -> str:
    if not historia:
        return "(brak poprzednich wiadomości)"
    lines = []
    for h in historia[-3:]:   # max 3 ostatnie wymiany
        lines.append(f"Osoba: {h.get('od', '')[:300]}")
        lines.append(f"Paweł: {h.get('odpowiedz', '')[:300]}")
    return "\n".join(lines)
