# Requiem Responder — dokumentacja programistyczna
**Data:** 5 marca 2026  
**Repozytorium:** https://github.com/legionowopawel/Requiem-Responder.git  
**Status:** v01 — stabilna, działa produkcyjnie

---

## Co program robi

Pośmiertny autoresponder Pawła. Gdy ktoś wyśle email ze słowem kluczowym `żyjesz`, program odpowiada tak jakby Paweł już nie żył i przebywa w zaświatach. Każda kolejna wiadomość od tej samej osoby przesuwa narrację do następnego etapu podróży pozagrobowej. Po 7 etapach Paweł informuje o reinkarnacji, a następnie odpowiada tajemniczy Wysłannik z wyższych sfer inspirowany Księgą Urantii.

---

## Przykładowy scenariusz

**Ewa pisze do Adama:**
```
Temat: hej
Treść: Adam, żyjesz? Nie odzywasz się od tygodnia...
```

**Adam (autoresponder) odpowiada:**
```
To autoresponder. Umarłem na suchoty dwudziestego szóstego lutego 
dwa tysiące dwudziestego szóstego roku. Właśnie wznoszę się tunelem 
światła — monety wypadają mi z kieszeni i spadają jak złote płatki 
śniegu. Jeśli znajdziesz którąś, uznaj to za zwrot długu.
```

**Ewa pisze ponownie:**
```
Co ty gadasz, zadzwoń do mnie!
```

**Adam (etap 2):**
```
Piszę z kolejki po paszport do zaświatów, która okazała się dłuższa 
niż do polskiego urzędu w piątek przed długim weekendem...
```

*...i tak przez 7 etapów, po czym Paweł informuje o reinkarnacji.*

---

## Architektura systemu

```
Gmail Ewy
    ↓  (email ze słowem "żyjesz")
Google Apps Script (GAS_smierc.js)
    ↓  co 10 minut skanuje skrzynkę
    ↓  sprawdza słowo kluczowe LUB czarną listę
    ↓  pobiera etap z Google Sheets
    ↓  POST /webhook_smierc
Render (app_smierc.py)
    ↓  Flask endpoint
    ↓  wywołuje smierc.py
    ↓  DeepSeek API
    ↓  zwraca reply_html + nowy_etap
Google Apps Script
    ↓  wysyła email do Ewy
    ↓  zapisuje wymianę do Google Sheets
Gmail Adama → Ewa otrzymuje odpowiedź
```

---

## Struktura plików

```
Requiem-Responder/
├── app_smierc.py           # Flask — endpoint /webhook_smierc
├── requirements.txt        # Flask, gunicorn, requests, python-dotenv
├── responders/
│   └── smierc.py           # logika odpowiedzi, tryby etap/wysłannik
├── core/
│   └── ai_client.py        # klient DeepSeek (skopiowany z głównego projektu)
└── prompts/
    └── pozagrobowe.txt     # 7 etapów po 3 wyrazy — rozwijane przez DeepSeek
```

### GAS (osobny skrypt Google Apps Script):
```
GAS_smierc.js
  _prop()                   # czyta Script Properties
  _dataSlownie()            # zamienia datę na tekst słowny po polsku
  _obliczDateSmierci()      # dziś minus 7 dni
  _getOrCreateSheet()       # tworzy zakładkę per osoba w Sheets
  _getEtap()                # pobiera aktualny etap osoby
  _getDataSmierci()         # pobiera datę śmierci (zapisaną przy pierwszym mailu)
  _getHistoria()            # pobiera 3 ostatnie wymiany (dla ciągłości DeepSeek)
  _zapiszWymiane()          # zapisuje mail + odpowiedź do Sheets
  _czyNaCzarnejLiscie()     # czy osoba ma już zakładkę w Sheets
  _callBackendSmierc()      # POST do Render
  _wyslijOdpowiedz()        # wysyła email (reply lub nowy)
  processSmierc()           # GŁÓWNA — trigger co 10 minut
  keepAliveSmierc()         # wybudza Render — trigger co 5 minut
```

---

## Google Sheets — struktura

**Jedna zakładka per osoba** (nazwa zakładki = email ze znakami @ i . zastąpionymi _)

Przykład zakładki `ewa_kowalska_gmail_com`:
```
A: nr  | B: data_smierci              | C: mail_od_osoby      | D: odpowiedz_pawla
1      | (nagłówek)                   | (nagłówek)            | (nagłówek)
2      | dwudziestego szóstego...     | żyjesz?               | To autoresponder...
3      |                              | co ty gadasz          | Piszę z kolejki...
4      |                              | zadzwoń do mnie       | Odprawa morontialna...
```

- `data_smierci` zapisywana **raz** w wierszu 2 — indywidualna dla każdej osoby
- Każda osoba ma **swoją własną datę śmierci** = dzień pierwszego maila minus 7 dni
- Historia (kolumny C i D) wysyłana do DeepSeeka dla zachowania ciągłości rozmowy

---

## Script Properties (GAS)

```
WEBHOOK_URL_SMIERC  =  https://requiem-responder.onrender.com/webhook_smierc
SHEET_ID_SMIERC     =  18oTMOt_G459ZyI6DfuphcORF81Zjh9YsRzSYq-Z-Ays
KEYWORD_SMIERC      =  żyjesz
```

---

## Zmienne środowiskowe (Render)

```
API_KEY_DEEPSEEK    =  (klucz DeepSeek)
PORT                =  10000
```

---

## Tryby odpowiedzi (smierc.py)

### Tryb ETAP (etap 1–6)
- DeepSeek dostaje: datę śmierci + treść etapu z `pozagrobowe.txt` + historię rozmowy
- Odpowiada jako Paweł w zaświatach
- Etap rośnie o 1 przy każdej odpowiedzi

### Tryb REINKARNACJA (etap 7)
- DeepSeek informuje że Paweł reinkarnuje się
- Pożegnanie, tajemnica gdzie się odrodzi
- Etap przechodzi na 8

### Tryb WYSŁANNIK (etap 8+)
- DeepSeek odpowiada jako tajemnicza istota z wyższych sfer
- Inspiracja Księgą Urantii (nie ujawniana wprost)
- Etap nie rośnie — Wysłannik odpowiada w nieskończoność

---

## Czarna lista

Każda osoba która napisała słowo kluczowe trafia automatycznie na czarną listę (ma zakładkę w Sheets). Od tego momentu **każda** jej wiadomość dostaje odpowiedź — bez względu na treść. Inne respondery (komiks, scrabble itp.) są w osobnym projekcie i nie kolidują.

---

## Katalog mediów (przygotowany, do wypełnienia)

```
requiem_media/
├── images/
│   ├── niebo/        # 1.png – 7.png  (obrazki etapów nieba)
│   ├── pieklo/       # 1.png – 7.png  (obrazki etapów — patrz: planowane)
│   └── wyslannik/    # wyslannik.png  (postać wysłannika)
└── mp4/
    ├── niebo/        # 1.mp4 – 7.mp4
    ├── pieklo/       # 1.mp4 – 7.mp4
    └── wyslannik.mp4
```

Program dobiera plik po numerze etapu: `images/niebo/3.png` dla etapu 3 wersji niebo.

---

## Planowane rozwinięcia

### 1. Wersja trudniejszej drogi (zamiast "piekła")
Księga Urantii nie mówi o piekle — mówi o trudniejszej, dłuższej drodze wznoszenia się. Planowane jest dodanie drugiej ścieżki narracyjnej gdzie Paweł trafił na trudniejszy szlak (ciemniejsze etapy, więcej prób i zadań). Losowanie ścieżki przy pierwszym mailu od danej osoby, zapisane w Sheets jako kolumna `wersja` (niebo / trudna_droga).

### 2. Obrazki AI przy reinkarnacji
Po etapie 7 (reinkarnacja) — generowanie obrazków przez FLUX na podstawie treści rozmowy. Wymaga tokenów HF i osobnego endpointu `/webhook_smierc_gif`. Wzór: zdjęcie Pawła jako punkt startowy dla AI image generation.

### 3. Wysłannik reklamuje niebo obrazkami
Gdy osoba pyta Wysłannika o konkretne rzeczy (np. "czy są tam kozy?") — DeepSeek generuje prompt dla FLUX który tworzy obrazek odpowiadający na pytanie (latające kolorowe kozy w niebie itp.). Odpowiedź tekstowa + obrazek AI.

### 4. Rozbudowa etapów do 100
Plik `pozagrobowe.txt` gotowy na rozbudowę — każdy punkt 3 wyrazy, DeepSeek go rozbudowuje. Przy etapie 100 powrót do etapu 1 lub specjalna odpowiedź.

### 5. Powiadomienie SMS
Gdy ktoś nowy trafi na czarną listę (pierwszy mail) — wysłanie SMS do Pawła przez Twilio lub podobny serwis.

---

## Zależności

| Biblioteka | Wersja | Do czego |
|---|---|---|
| Flask | >=2.2.5 | serwer HTTP |
| gunicorn | >=20.1.0 | serwer produkcyjny |
| requests | >=2.31.0 | wywołania HTTP (DeepSeek) |
| python-dotenv | >=1.0.0 | zmienne środowiskowe |

---

## Start Command (Render)

```
gunicorn app_smierc:app
```

---

*Dokument wygenerowany 5 marca 2026. Przy następnej sesji wgraj ten plik i opisz co chcesz rozbudować.*
