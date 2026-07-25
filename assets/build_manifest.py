#!/usr/bin/env python3
"""Extract learner-facing Kannada from lessons/ and write assets/audio/manifest.json.

Roman is the learner-facing form; `kannada` (script) drives TTS.
Dedupe by normalized roman content so spaced repetition reuses one clip.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "lessons"
OUT = ROOT / "assets" / "audio" / "manifest.json"

# ---------------------------------------------------------------------------
# Roman → Kannada script (Bengaluru spoken forms as used in the course)
# Keys are lowercased roman without trailing ? for lookup flexibility.
# ---------------------------------------------------------------------------
KN: dict[str, str] = {
    # L1
    "namaskara": "ನಮಸ್ಕಾರ",
    "hegiddiri": "ಹೇಗಿದ್ದೀರಿ",
    "chennagidini": "ಚೆನ್ನಾಗಿದ್ದೀನಿ",
    "neevu": "ನೀವು",
    "nimma": "ನಿಮ್ಮ",
    "nanna": "ನನ್ನ",
    "hesaru": "ಹೆಸರು",
    "enu": "ಏನು",
    "dhanyavadagalu": "ಧನ್ಯವಾದಗಳು",
    "sari": "ಸರಿ",
    "nimma hesaru enu": "ನಿಮ್ಮ ಹೆಸರು ಏನು",
    "nanna hesaru prayank": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "nanna hesaru ravi": "ನನ್ನ ಹೆಸರು ರವಿ",
    "nanna hesaru ravi. nimma": "ನನ್ನ ಹೆಸರು ರವಿ. ನಿಮ್ಮ",
    "nimma?": "ನಿಮ್ಮ?",
    # L2
    "elli": "ಎಲ್ಲಿ",
    "hogtiddiri": "ಹೋಗ್ತಿದ್ದೀರಿ",
    "hogtidini": "ಹೋಗ್ತಿದೀನಿ",
    "naanu": "ನಾನು",
    "mane": "ಮನೆ",
    "manege": "ಮನೆಗೆ",
    "kelasa": "ಕೆಲಸ",
    "kelasa-ge": "ಕೆಲಸಕ್ಕೆ",
    "kelasa-ge hogtidini": "ಕೆಲಸಕ್ಕೆ ಹೋಗ್ತಿದೀನಿ",
    "illi": "ಇಲ್ಲಿ",
    "alli": "ಅಲ್ಲಿ",
    "nodona": "ನೋಡೋಣ",
    "olle": "ಒಳ್ಳೆ",
    "dinagalu": "ದಿನಗಳು",
    "olle dinagalu": "ಒಳ್ಳೆ ದಿನಗಳು",
    "elli hogtiddiri": "ಎಲ್ಲಿ ಹೋಗ್ತಿದ್ದೀರಿ",
    "naanu manege hogtidini": "ನಾನು ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ",
    "office-ge hogtidini": "ಆಫೀಸ್‌ಗೆ ಹೋಗ್ತಿದೀನಿ",
    "naanu office-ge hogtidini": "ನಾನು ಆಫೀಸ್‌ಗೆ ಹೋಗ್ತಿದೀನಿ",
    "sari, nodona": "ಸರಿ, ನೋಡೋಣ",
    "hogtini, sari": "ಹೋಗ್ತೀನಿ, ಸರಿ",
    "hogtini": "ಹೋಗ್ತೀನಿ",
    "market-ge": "ಮಾರ್ಕೆಟ್‌ಗೆ",
    "market-ge. neevu": "ಮಾರ್ಕೆಟ್‌ಗೆ. ನೀವು",
    "sari. dhanyavadagalu": "ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "chennagidini. neevu": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ನೀವು",
    "chennagidini. elli hogtiddiri": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಎಲ್ಲಿ ಹೋಗ್ತಿದ್ದೀರಿ",
    "namaskara. hegiddiri": "ನಮಸ್ಕಾರ. ಹೇಗಿದ್ದೀರಿ",
    "naanu office-ge hogtidini. sari, nodona. olle dinagalu": (
        "ನಾನು ಆಫೀಸ್‌ಗೆ ಹೋಗ್ತಿದೀನಿ. ಸರಿ, ನೋಡೋಣ. ಒಳ್ಳೆ ದಿನಗಳು"
    ),
    "nanna hesaru prayank. dhanyavadagalu": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ಧನ್ಯವಾದಗಳು",
    "namaskara. hegiddiri?": "ನಮಸ್ಕಾರ. ಹೇಗಿದ್ದೀರಿ?",
    "namaskara. hegiddiri": "ನಮಸ್ಕಾರ. ಹೇಗಿದ್ದೀರಿ",
    # L3 numbers + money
    "eshtu": "ಎಷ್ಟು",
    "idhu": "ಇದು",
    "adhu": "ಅದು",
    "rupayi": "ರೂಪಾಯಿ",
    "swalpa": "ಸ್ವಲ್ಪ",
    "kammi": "ಕಮ್ಮಿ",
    "maadi": "ಮಾಡಿ",
    "jaasti": "ಜಾಸ್ತಿ",
    "aytu": "ಆಯ್ತು",
    "beda": "ಬೇಡ",
    "ondu": "ಒಂದು",
    "eradu": "ಎರಡು",
    "mooru": "ಮೂರು",
    "naalku": "ನಾಲ್ಕು",
    "aidu": "ಐದು",
    "aaru": "ಆರು",
    "elu": "ಏಳು",
    "entu": "ಎಂಟು",
    "ombattu": "ಒಂಬತ್ತು",
    "hattu": "ಹತ್ತು",
    "hadinaru": "ಹದಿನಾರು",
    "ippatthu": "ಇಪ್ಪತ್ತು",
    "moovattu": "ಮೂವತ್ತು",
    "nalavattu": "ನಲವತ್ತು",
    "aivattu": "ಐವತ್ತು",
    "nooru": "ನೂರು",
    "idhu eshtu": "ಇದು ಎಷ್ಟು",
    "adhu eshtu": "ಅದು ಎಷ್ಟು",
    "swalpa kammi maadi": "ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ",
    "jaasti aytu": "ಜಾಸ್ತಿ ಆಯ್ತು",
    "meter haki": "ಮೀಟರ್ ಹಾಕಿ",
    "haki": "ಹಾಕಿ",
    "alli eshtu": "ಅಲ್ಲಿ ಎಷ್ಟು",
    "koramangala-ge eshtu": "ಕೋರಮಂಗಲಕ್ಕೆ ಎಷ್ಟು",
    "indiranagar-ge eshtu": "ಇಂದಿರಾನಗರಕ್ಕೆ ಎಷ್ಟು",
    "hogona": "ಹೋಗೋಣ",
    "hattu rupayi": "ಹತ್ತು ರೂಪಾಯಿ",
    "entu rupayi sari": "ಎಂಟು ರೂಪಾಯಿ ಸರಿ",
    "jaasti aytu. meter haki": "ಜಾಸ್ತಿ ಆಯ್ತು. ಮೀಟರ್ ಹಾಕಿ",
    "sari, haki": "ಸರಿ, ಹಾಕಿ",
    "sari. hogona": "ಸರಿ. ಹೋಗೋಣ",
    "namaskara. idhu eshtu": "ನಮಸ್ಕಾರ. ಇದು ಎಷ್ಟು",
    "namaskara. idhu eshtu?": "ನಮಸ್ಕಾರ. ಇದು ಎಷ್ಟು?",
    # L4 directions
    "ide": "ಇದೆ",
    "elli ide": "ಎಲ್ಲಿ ಇದೆ",
    "heghe": "ಹೇಗೆ",
    "hogbeku": "ಹೋಗಬೇಕು",
    "heghe hogbeku": "ಹೇಗೆ ಹೋಗಬೇಕು",
    "eduru": "ಎದುರು",
    "nera": "ನೇರ",
    "balakke": "ಬಲಕ್ಕೆ",
    "yedakke": "ಎಡಕ್ಕೆ",
    "thirgi": "ತಿರುಗಿ",
    "nantara": "ನಂತರ",
    "hattira": "ಹತ್ತಿರ",
    "dooradalli": "ದೂರದಲ್ಲಿ",
    "idhe": "ಇದೇ",
    "idhe na": "ಇದೇ ನಾ",
    "alli na": "ಅಲ್ಲಿ ನಾ",
    "gothaytu": "ಗೊತ್ತಾಯ್ತು",
    "gottila": "ಗೊತ್ತಿಲ್ಲ",
    "gothilla": "ಗೊತ್ತಿಲ್ಲ",
    "haudu": "ಹೌದು",
    "eduru hogi": "ಎದುರು ಹೋಗಿ",
    "hogi": "ಹೋಗಿ",
    "balakke thirgi": "ಬಲಕ್ಕೆ ತಿರುಗಿ",
    "yedakke thirgi": "ಎಡಕ್ಕೆ ತಿರುಗಿ",
    "swalpa eduru, nantara balakke": "ಸ್ವಲ್ಪ ಎದುರು, ನಂತರ ಬಲಕ್ಕೆ",
    "clubhouse elli ide": "ಕ್ಲಬ್‌ಹೌಸ್ ಎಲ್ಲಿ ಇದೆ",
    "clubhouse elli ide?": "ಕ್ಲಬ್‌ಹೌಸ್ ಎಲ್ಲಿ ಇದೆ?",
    "gate elli ide": "ಗೇಟ್ ಎಲ್ಲಿ ಇದೆ",
    "gate elli ide?": "ಗೇಟ್ ಎಲ್ಲಿ ಇದೆ?",
    "namaskara. clubhouse elli ide": "ನಮಸ್ಕಾರ. ಕ್ಲಬ್‌ಹೌಸ್ ಎಲ್ಲಿ ಇದೆ",
    "namaskara. clubhouse elli ide?": "ನಮಸ್ಕಾರ. ಕ್ಲಬ್‌ಹೌಸ್ ಎಲ್ಲಿ ಇದೆ?",
    "eduru hogi. nantara balakke": "ಎದುರು ಹೋಗಿ. ನಂತರ ಬಲಕ್ಕೆ",
    "swalpa eduru, nantara balakke — idhe na": "ಸ್ವಲ್ಪ ಎದುರು, ನಂತರ ಬಲಕ್ಕೆ — ಇದೇ ನಾ",
    "swalpa eduru, nantara balakke — idhe na?": "ಸ್ವಲ್ಪ ಎದುರು, ನಂತರ ಬಲಕ್ಕೆ — ಇದೇ ನಾ?",
    "haudu. hattira ide": "ಹೌದು. ಹತ್ತಿರ ಇದೆ",
    "gothaytu. dhanyavadagalu": "ಗೊತ್ತಾಯ್ತು. ಧನ್ಯವಾದಗಳು",
    # L5 food
    "beku": "ಬೇಕು",
    "kodri": "ಕೊಡ್ರಿ",
    "neeru": "ನೀರು",
    "oota": "ಊಟ",
    "cha": "ಚಾ",
    "iggade": "ಇಗ್ಗಡೆ",
    "innu": "ಇನ್ನೂ",
    "nimisha": "ನಿಮಿಷ",
    "gottu": "ಗೊತ್ತು",
    "coffee ondu kodri": "ಕಾಫಿ ಒಂದು ಕೊಡ್ರಿ",
    "idli eradu beku": "ಇಡ್ಲಿ ಎರಡು ಬೇಕು",
    "masala dosa ondu kodri": "ಮಸಾಲೆ ದೋಸೆ ಒಂದು ಕೊಡ್ರಿ",
    "neeru kodri": "ನೀರು ಕೊಡ್ರಿ",
    "swalpa less sweet": "ಸ್ವಲ್ಪ ಲೆಸ್ ಸ್ವೀಟ್",
    "strong maadi": "ಸ್ಟ್ರಾಂಗ್ ಮಾಡಿ",
    "parcel maadi": "ಪಾರ್ಸೆಲ್ ಮಾಡಿ",
    "bill kodri": "ಬಿಲ್ ಕೊಡ್ರಿ",
    "eshtu aytu": "ಎಷ್ಟು ಆಯ್ತು",
    "innu eradu nimisha": "ಇನ್ನೂ ಎರಡು ನಿಮಿಷ",
    "filter coffee ondu kodri": "ಫಿಲ್ಟರ್ ಕಾಫಿ ಒಂದು ಕೊಡ್ರಿ",
    "namaskara. filter coffee ondu kodri. idli eradu beku": (
        "ನಮಸ್ಕಾರ. ಫಿಲ್ಟರ್ ಕಾಫಿ ಒಂದು ಕೊಡ್ರಿ. ಇಡ್ಲಿ ಎರಡು ಬೇಕು"
    ),
    "iggade na": "ಇಗ್ಗಡೆ ನಾ",
    "iggade na? parcel na": "ಇಗ್ಗಡೆ ನಾ? ಪಾರ್ಸೆಲ್ ನಾ",
    "iggade na? parcel na?": "ಇಗ್ಗಡೆ ನಾ? ಪಾರ್ಸೆಲ್ ನಾ?",
    "iggade. neeru kodri": "ಇಗ್ಗಡೆ. ನೀರು ಕೊಡ್ರಿ",
    "sari… coffee ready": "ಸರಿ. ಕಾಫಿ ರೆಡಿ",
    "sari... coffee ready": "ಸರಿ. ಕಾಫಿ ರೆಡಿ",
    "sari. coffee ready": "ಸರಿ. ಕಾಫಿ ರೆಡಿ",
    "swalpa barutte": "ಸ್ವಲ್ಪ ಬರುತ್ತೆ",
    "bill kodri. eshtu aytu": "ಬಿಲ್ ಕೊಡ್ರಿ. ಎಷ್ಟು ಆಯ್ತು",
    "bill kodri. eshtu aytu?": "ಬಿಲ್ ಕೊಡ್ರಿ. ಎಷ್ಟು ಆಯ್ತು?",
    "aivattu rupayi": "ಐವತ್ತು ರೂಪಾಯಿ",
    # L6 politeness
    "kshamisi": "ಕ್ಷಮಿಸಿ",
    "dayavittu": "ದಯವಿಟ್ಟು",
    "sahaya": "ಸಹಾಯ",
    "sahaya maadi": "ಸಹಾಯ ಮಾಡಿ",
    "tumba": "ತುಂಬಾ",
    "nanage": "ನನಗೆ",
    "matte": "ಮತ್ತೆ",
    "sigona": "ಸಿಗೋಣ",
    "barutte": "ಬರುತ್ತೆ",
    "swalpa wait maadi": "ಸ್ವಲ್ಪ ವೇಟ್ ಮಾಡಿ",
    "innu ondu nimisha": "ಇನ್ನೂ ಒಂದು ನಿಮಿಷ",
    "tumba sorry": "ತುಂಬಾ ಸಾರಿ",
    "kshamisi maadi": "ಕ್ಷಮಿಸಿ ಮಾಡಿ",
    "tumba dhanyavadagalu": "ತುಂಬಾ ಧನ್ಯವಾದಗಳು",
    "tumba thanks": "ತುಂಬಾ ಥ್ಯಾಂಕ್ಸ್",
    "nanage gothilla": "ನನಗೆ ಗೊತ್ತಿಲ್ಲ",
    "nanage gottila": "ನನಗೆ ಗೊತ್ತಿಲ್ಲ",
    "kannada swalpa swalpa barutte": "ಕನ್ನಡ ಸ್ವಲ್ಪ ಸ್ವಲ್ಪ ಬರುತ್ತೆ",
    "english ok": "ಇಂಗ್ಲಿಷ್ ಓಕೆ",
    "english ok?": "ಇಂಗ್ಲಿಷ್ ಓಕೆ?",
    "matte sigona": "ಮತ್ತೆ ಸಿಗೋಣ",
    "sari hogi": "ಸರಿ ಹೋಗಿ",
    "kshamisi. dayavittu, metro gate elli ide": (
        "ಕ್ಷಮಿಸಿ. ದಯವಿಟ್ಟು, ಮೆಟ್ರೋ ಗೇಟ್ ಎಲ್ಲಿ ಇದೆ"
    ),
    "kshamisi. dayavittu, metro gate elli ide?": (
        "ಕ್ಷಮಿಸಿ. ದಯವಿಟ್ಟು, ಮೆಟ್ರೋ ಗೇಟ್ ಎಲ್ಲಿ ಇದೆ?"
    ),
    "eduru hogi…": "ಎದುರು ಹೋಗಿ",
    "eduru hogi...": "ಎದುರು ಹೋಗಿ",
    "gothaytu. tumba dhanyavadagalu": "ಗೊತ್ತಾಯ್ತು. ತುಂಬಾ ಧನ್ಯವಾದಗಳು",
    "tumba sorry! kshamisi": "ತುಂಬಾ ಸಾರಿ! ಕ್ಷಮಿಸಿ",
    "tumba sorry! kshamisi.": "ತುಂಬಾ ಸಾರಿ! ಕ್ಷಮಿಸಿ",
    "dayavittu sahaya maadi — bag beelitu": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ — ಬ್ಯಾಗ್ ಬೀಳ್ತು",
    "dayavittu sahaya maadi — bag beelitu.": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ — ಬ್ಯಾಗ್ ಬೀಳ್ತು",
    "sari sari": "ಸರಿ ಸರಿ",
    "sari sari.": "ಸರಿ ಸರಿ",
    # grammar particles learners hear
    "-ge": "ಗೆ",
    "ge": "ಗೆ",
    # L7 time-of-day
    "shubhodaya": "ಶುಭೋದಯ",
    "shubha": "ಶುಭ",
    "shubha madhyahna": "ಶುಭ ಮಧ್ಯಾಹ್ನ",
    "shubha sayankala": "ಶುಭ ಸಾಯಂಕಾಲ",
    "shubharatri": "ಶುಭರಾತ್ರಿ",
    "beligge": "ಬೆಳಿಗ್ಗೆ",
    "madhyahna": "ಮಧ್ಯಾಹ್ನ",
    "sayankala": "ಸಾಯಂಕಾಲ",
    "ratri": "ರಾತ್ರಿ",
    "ivattu": "ಇವತ್ತು",
    "naale": "ನಾಳೆ",
    "ninne": "ನಿನ್ನೆ",
    "naale nodona": "ನಾಳೆ ನೋಡೋಣ",
    "hogi banni": "ಹೋಗಿ ಬನ್ನಿ",
    "shubha dinavagali": "ಶುಭ ದಿನವಾಗಲಿ",
    "olleyadagali": "ಒಳ್ಳೆಯದಾಗಲಿ",
    "yaavaaga": "ಯಾವಾಗ",
    "yaavaaga?": "ಯಾವಾಗ?",
    "shubhodaya. hegiddiri": "ಶುಭೋದಯ. ಹೇಗಿದ್ದೀರಿ",
    "shubhodaya. hegiddiri?": "ಶುಭೋದಯ. ಹೇಗಿದ್ದೀರಿ?",
    "chennagidini. sari, hogi banni. shubha dinavagali": (
        "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಸರಿ, ಹೋಗಿ ಬನ್ನಿ. ಶುಭ ದಿನವಾಗಲಿ"
    ),
    "namaskara. shubha sayankala": "ನಮಸ್ಕಾರ. ಶುಭ ಸಾಯಂಕಾಲ",
    "shubha sayankala. elli hogtiddiri": "ಶುಭ ಸಾಯಂಕಾಲ. ಎಲ್ಲಿ ಹೋಗ್ತಿದ್ದೀರಿ",
    "shubha sayankala. elli hogtiddiri?": "ಶುಭ ಸಾಯಂಕಾಲ. ಎಲ್ಲಿ ಹೋಗ್ತಿದ್ದೀರಿ?",
    "naanu manege hogtidini. naale nodona": "ನಾನು ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ. ನಾಳೆ ನೋಡೋಣ",
    "sari. shubharatri": "ಸರಿ. ಶುಭರಾತ್ರಿ",
    # L8 numbers 11–20 + money stretch
    "hannondu": "ಹನ್ನೊಂದು",
    "hanneradu": "ಹನ್ನೆರಡು",
    "hadimooru": "ಹದಿಮೂರು",
    "hadinaalku": "ಹದಿನಾಲ್ಕು",
    "hadinaidu": "ಹದಿನೈದು",
    "hadinaru": "ಹದಿನಾರು",
    "hadinelu": "ಹದಿನೇಳು",
    "hadinentu": "ಹದಿನೆಂಟು",
    "hattombattu": "ಹತ್ತೊಂಬತ್ತು",
    "ippatthu": "ಇಪ್ಪತ್ತು",
    "alla": "ಅಲ್ಲ",
    "hadinaidu rupayi": "ಹದಿನೈದು ರೂಪಾಯಿ",
    "ippatthu rupayi sari na": "ಇಪ್ಪತ್ತು ರೂಪಾಯಿ ಸರಿ ನಾ",
    "ippatthu rupayi sari na?": "ಇಪ್ಪತ್ತು ರೂಪಾಯಿ ಸರಿ ನಾ?",
    "hanneradu idli": "ಹನ್ನೆರಡು ಇಡ್ಲಿ",
    "hadimooru coffee": "ಹದಿಮೂರು ಕಾಫಿ",
    "eshtu? — hadinaru": "ಎಷ್ಟು? ಹದಿನಾರು",
    "eshtu? — hadinaru.": "ಎಷ್ಟು? ಹದಿನಾರು",
    "eshtu — hadinaru": "ಎಷ್ಟು? ಹದಿನಾರು",
    "ippatthu-ge swalpa kammi maadi": "ಇಪ್ಪತ್ತಕ್ಕೆ ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ",
    "nooru alla — aivattu": "ನೂರು ಅಲ್ಲ — ಐವತ್ತು",
    "nooru alla": "ನೂರು ಅಲ್ಲ",
    "hadinentu rupayi": "ಹದಿನೆಂಟು ರೂಪಾಯಿ",
    "hadinentu rupayi.": "ಹದಿನೆಂಟು ರೂಪಾಯಿ",
    "hadinentu… swalpa kammi maadi. hadinaru sari na": (
        "ಹದಿನೆಂಟು. ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ. ಹದಿನಾರು ಸರಿ ನಾ"
    ),
    "hadinentu. swalpa kammi maadi. hadinaru sari na": (
        "ಹದಿನೆಂಟು. ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ. ಹದಿನಾರು ಸರಿ ನಾ"
    ),
    "hadinentu. swalpa kammi maadi. hadinaru sari na?": (
        "ಹದಿನೆಂಟು. ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ. ಹದಿನಾರು ಸರಿ ನಾ?"
    ),
    "sari, hadinaidu": "ಸರಿ, ಹದಿನೈದು",
    "sari, hadinaidu.": "ಸರಿ, ಹದಿನೈದು",
    "hadinaru sari na": "ಹದಿನಾರು ಸರಿ ನಾ",
    "hadinaru sari na?": "ಹದಿನಾರು ಸರಿ ನಾ?",
}

# Pure English / non-spoken chrome to skip when standalone
DROP_STANDALONE = {
    "en",
    "english",
    "yes",
    "water bottle",
    "right",
    "left",
    "straight",
    "filter coffee",
    "masala dosa",
    "coffee",
    "tea",
    "idli",
    "vada",
    "dosa",
    "upma",
    "poori",
    "meals",
    "water",
    "bill",
    "parcel",
    "meter",
    "fix",
    "strong",
    "wait",
    "thanks",
    "sorry",
    "office",
    "market",
    "shop",
    "gym",
    "clubhouse",
    "restroom",
    "gate",
    "medical",
    "indiranagar",
    "koramangala",
    "prayank",
    "ravi",
    "less sweet",
    "fix a?",
    "ondu…hattu",
    "ondu...hattu",
    "water / neeru",
}


def norm_roman(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def lookup_key(roman: str) -> str:
    s = norm_roman(roman).lower()
    s = s.replace("?", "")
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s


def to_kannada(roman: str) -> str | None:
    r = norm_roman(roman)
    # direct
    for key in (r.lower(), lookup_key(r), r.lower().rstrip(".!")):
        if key in KN:
            return KN[key]
        k2 = key.rstrip(".")
        if k2 in KN:
            return KN[k2]
    # try without final punctuation
    k = lookup_key(r)
    if k in KN:
        return KN[k]
    # multi-sentence: join known pieces
    parts = re.split(r"(?<=[.!?])\s+", r)
    if len(parts) > 1:
        out = []
        for p in parts:
            pk = lookup_key(p)
            if pk in KN:
                out.append(KN[pk])
            elif p.lower().rstrip(".!? ") in KN:
                out.append(KN[p.lower().rstrip(".!? ")])
            else:
                return None
        return " ".join(out)
    return None


def slugify(s: str) -> str:
    s = s.lower().strip()
    # leading particle markers
    if s in ("-ge", "ge", "‑ge"):
        return "particle_ge"
    s = s.replace("?", "").replace("!", "").replace(",", "").replace(".", "")
    s = s.replace("·", " ").replace("/", " ").replace("—", " ").replace("–", " ")
    s = s.replace("'", "").replace("'", "")
    s = s.lstrip("-_")
    s = re.sub(r"[^a-z0-9\s_-]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    s = re.sub(r"_+", "_", s)
    return (s[:72] or "item")


def add(bucket: dict, roman: str, lid: str, kind: str) -> None:
    roman = norm_roman(roman)
    if not roman:
        return
    if "…" in roman or "..." in roman:
        # normalize ellipsis dialogue to clean form when possible
        cleaned = roman.replace("…", ".").replace("...", ".")
        cleaned = re.sub(r"\s*\.\s*", ". ", cleaned).strip(" .")
        if cleaned:
            roman = cleaned if kind == "dialogue" else roman
            if "…" in roman or "..." in roman:
                if kind != "dialogue":
                    return
                roman = cleaned
    k = roman.lower()
    rl = lookup_key(roman)
    if rl in DROP_STANDALONE or roman.lower() in DROP_STANDALONE:
        return
    if k not in bucket:
        bucket[k] = {"roman": roman, "lessons": set(), "kind": kind}
    bucket[k]["lessons"].add(lid)
    if kind == "dialogue":
        bucket[k]["kind"] = "dialogue"


def extract() -> tuple[dict, dict]:
    words: dict = {}
    sents: dict = {}
    for f in sorted(LESSONS.glob("*.html")):
        lid = f.stem.split("-")[0]
        html = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<p class="kn">(.*?)</p>', html, re.S):
            t = re.sub(r"<[^>]+>", "", m.group(1))
            t = norm_roman(t)
            for p in re.split(r"\s*·\s*", t):
                p = p.strip()
                if not p or p in ("…", "..."):
                    continue
                if " / " in p and len(p) < 48:
                    for q in p.split(" / "):
                        q = q.strip()
                        if not q:
                            continue
                        if " " in q or q.endswith("?"):
                            add(sents, q, lid, "phrase")
                        else:
                            add(words, q, lid, "word")
                else:
                    if " " in p or p.endswith("?"):
                        add(sents, p, lid, "phrase")
                    else:
                        add(words, p, lid, "word")
        for m in re.finditer(r'<span class="kn">(.*?)</span>', html, re.S):
            t = re.sub(r"<[^>]+>", "", m.group(1))
            t = norm_roman(t)
            for p in re.split(r"\s*[·/]\s*", t):
                p = p.strip()
                if not p or "…" in p or "..." in p:
                    continue
                if " " in p:
                    add(sents, p, lid, "vocab_phrase")
                else:
                    add(words, p, lid, "word")
        for m in re.finditer(r'<span class="line">(.*?)</span>', html, re.S):
            t = re.sub(r"<[^>]+>", "", m.group(1))
            t = norm_roman(t)
            if t:
                add(sents, t, lid, "dialogue")
    return words, sents


def main() -> None:
    words, sents = extract()

    final_words: dict = {}
    for k, v in words.items():
        r = v["roman"]
        if lookup_key(r) in DROP_STANDALONE:
            continue
        if "…" in r or "..." in r:
            continue
        final_words[k] = v

    final_sents: dict = {}
    for k, v in sents.items():
        r = v["roman"]
        # single-token non-dialogue → word
        if " " not in r and v.get("kind") != "dialogue":
            if lookup_key(r) not in DROP_STANDALONE:
                kk = r.lower()
                if kk not in final_words:
                    final_words[kk] = {
                        "roman": r,
                        "lessons": set(v["lessons"]),
                        "kind": "word",
                    }
                else:
                    final_words[kk]["lessons"] |= v["lessons"]
            continue
        final_sents[k] = v

    # Promote multi-word phrases; keep single-word questions as words primarily
    # but also as sentences if they end with ? and appear as phrases (slow+nat useful)
    for k, v in list(final_words.items()):
        r = v["roman"]
        if r.endswith("?") and " " not in r:
            # also sentence for slow/nat practice
            sk = r.lower()
            if sk not in final_sents:
                final_sents[sk] = {
                    "roman": r,
                    "lessons": set(v["lessons"]),
                    "kind": "phrase",
                }
            else:
                final_sents[sk]["lessons"] |= v["lessons"]

    seen_slugs: set[str] = set()

    def unique_slug(roman: str) -> str:
        base = slugify(roman)
        slug = base
        i = 2
        while slug in seen_slugs:
            slug = f"{base}_{i}"
            i += 1
        seen_slugs.add(slug)
        return slug

    entries = []
    missing_script = []

    for v in sorted(final_words.values(), key=lambda x: x["roman"].lower()):
        kn = to_kannada(v["roman"])
        slug = unique_slug(v["roman"])
        if not kn:
            missing_script.append(("word", v["roman"]))
            continue
        entries.append(
            {
                "slug": slug,
                "type": "word",
                "roman": v["roman"],
                "kannada": kn,
                "lessons": sorted(v["lessons"]),
                "files": [f"{slug}.mp3"],
            }
        )

    for v in sorted(final_sents.values(), key=lambda x: x["roman"].lower()):
        kn = to_kannada(v["roman"])
        slug = unique_slug(v["roman"])
        if not kn:
            missing_script.append(("sentence", v["roman"]))
            continue
        entries.append(
            {
                "slug": slug,
                "type": "sentence",
                "roman": v["roman"],
                "kannada": kn,
                "kind": v.get("kind", "phrase"),
                "lessons": sorted(v["lessons"]),
                "files": [f"{slug}_slow.mp3", f"{slug}_nat.mp3"],
            }
        )

    # Also index by roman lower for lesson retrofit
    by_roman = {e["roman"].lower(): e for e in entries}
    # strip ? variants
    for e in entries:
        by_roman[e["roman"].lower().rstrip("?.!")] = e

    manifest = {
        "version": 1,
        "tts": {
            "engine": "edge-tts",
            "voice": "kn-IN-SapnaNeural",
            "note": "Machine-generated Kannada. May not perfectly match native Bengaluru speech.",
            "rates": {"word": "+0%", "sentence_nat": "+0%", "sentence_slow": "-35%"},
        },
        "entries": entries,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"  words:     {sum(1 for e in entries if e['type']=='word')}")
    print(f"  sentences: {sum(1 for e in entries if e['type']=='sentence')}")
    print(f"  clips:     {sum(len(e['files']) for e in entries)}")
    if missing_script:
        print(f"\nMISSING KANNADA SCRIPT ({len(missing_script)}):")
        for kind, roman in missing_script:
            print(f"  [{kind}] {roman}")
    else:
        print("\nAll entries have Kannada script.")


if __name__ == "__main__":
    main()
