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
    # L9 clock time
    "gante": "ಗಂಟೆ",
    "ardha": "ಅರ್ಧ",
    "eega": "ಈಗ",
    "banni": "ಬನ್ನಿ",
    "eshtu gante": "ಎಷ್ಟು ಗಂಟೆ",
    "eshtu gante?": "ಎಷ್ಟು ಗಂಟೆ?",
    "eshtu gante aytu": "ಎಷ್ಟು ಗಂಟೆ ಆಯ್ತು",
    "eshtu gante aytu?": "ಎಷ್ಟು ಗಂಟೆ ಆಯ್ತು?",
    "aidu gante": "ಐದು ಗಂಟೆ",
    "aidu gante aytu": "ಐದು ಗಂಟೆ ಆಯ್ತು",
    "mooru gante": "ಮೂರು ಗಂಟೆ",
    "elu gante": "ಏಳು ಗಂಟೆ",
    "hattu gante": "ಹತ್ತು ಗಂಟೆ",
    "hattu gante aytu": "ಹತ್ತು ಗಂಟೆ ಆಯ್ತು",
    "hanneradu gante": "ಹನ್ನೆರಡು ಗಂಟೆ",
    "hattu gante-ge banni": "ಹತ್ತು ಗಂಟೆಗೆ ಬನ್ನಿ",
    "naale elu gante-ge": "ನಾಳೆ ಏಳು ಗಂಟೆಗೆ",
    "aidu gante ardha": "ಐದು ಗಂಟೆ ಅರ್ಧ",
    "eega · tumba late aytu": "ಈಗ. ತುಂಬಾ ಲೇಟ್ ಆಯ್ತು",
    "tumba late aytu": "ತುಂಬಾ ಲೇಟ್ ಆಯ್ತು",
    "late aytu": "ಲೇಟ್ ಆಯ್ತು",
    "swalpa early": "ಸ್ವಲ್ಪ ಅರ್ಲಿ",
    "time ide na": "ಟೈಮ್ ಇದೆ ನಾ",
    "time ide na?": "ಟೈಮ್ ಇದೆ ನಾ?",
    "yaavaaga meeting": "ಯಾವಾಗ ಮೀಟಿಂಗ್",
    "yaavaaga meeting?": "ಯಾವಾಗ ಮೀಟಿಂಗ್?",
    "hattu gante-ge": "ಹತ್ತು ಗಂಟೆಗೆ",
    "kshamisi. eshtu gante aytu": "ಕ್ಷಮಿಸಿ. ಎಷ್ಟು ಗಂಟೆ ಆಯ್ತು",
    "kshamisi. eshtu gante aytu?": "ಕ್ಷಮಿಸಿ. ಎಷ್ಟು ಗಂಟೆ ಆಯ್ತು?",
    "hattu gante aytu.": "ಹತ್ತು ಗಂಟೆ ಆಯ್ತು",
    "gothaytu. dhanyavadagalu": "ಗೊತ್ತಾಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "naale beligge elu gante-ge": "ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಏಳು ಗಂಟೆಗೆ",
    "sari. elu gante ardha ok na": "ಸರಿ. ಏಳು ಗಂಟೆ ಅರ್ಧ ಓಕೆ ನಾ",
    "sari. elu gante ardha ok na?": "ಸರಿ. ಏಳು ಗಂಟೆ ಅರ್ಧ ಓಕೆ ನಾ?",
    "elu gante ardha ok na": "ಏಳು ಗಂಟೆ ಅರ್ಧ ಓಕೆ ನಾ",
    "elu gante ardha ok na?": "ಏಳು ಗಂಟೆ ಅರ್ಧ ಓಕೆ ನಾ?",
    "sari. naale nodona": "ಸರಿ. ನಾಳೆ ನೋಡೋಣ",
    "nantara / baadige": "ನಂತರ",
    "baadige": "ಬಾದಿಗೆ",
    "nimisha": "ನಿಮಿಷ",
    # L10 phone call
    "halo": "ಹಲೋ",
    "kare": "ಕರೆ",
    "phone": "ಫೋನ್",
    "number": "ನಂಬರ್",
    "yaaru": "ಯಾರು",
    "maatadu": "ಮಾತಾಡು",
    "maatadtiddira": "ಮಾತಾಡ್ತಿದ್ದೀರಾ",
    "kaayri": "ಕಾಯ್ರಿ",
    "avaru": "ಅವರು",
    "illa": "ಇಲ್ಲ",
    "tappa": "ತಪ್ಪ",
    "aagide": "ಆಗಿದೆ",
    "iddara": "ಇದ್ದಾರಾ",
    "help": "ಹೆಲ್ಪ್",
    "line": "ಲೈನ್",
    "busy": "ಬಿಸಿ",
    "nanage kare maadi": "ನನಗೆ ಕರೆ ಮಾಡಿ",
    "naanu phone maadtini": "ನಾನು ಫೋನ್ ಮಾಡ್ತೀನಿ",
    "ondu nimisha kaayri": "ಒಂದು ನಿಮಿಷ ಕಾಯ್ರಿ",
    "ondu nimisha": "ಒಂದು ನಿಮಿಷ",
    "yaaru maatadtiddira": "ಯಾರು ಮಾತಾಡ್ತಿದ್ದೀರಾ",
    "yaaru maatadtiddira?": "ಯಾರು ಮಾತಾಡ್ತಿದ್ದೀರಾ?",
    "avaru eega illa": "ಅವರು ಈಗ ಇಲ್ಲ",
    "tappa number": "ತಪ್ಪ ನಂಬರ್",
    "line busy aagide": "ಲೈನ್ ಬಿಸಿ ಆಗಿದೆ",
    "line busy": "ಲೈನ್ ಬಿಸಿ",
    "nimma phone number eshtu": "ನಿಮ್ಮ ಫೋನ್ ನಂಬರ್ ಎಷ್ಟು",
    "nimma phone number eshtu?": "ನಿಮ್ಮ ಫೋನ್ ನಂಬರ್ ಎಷ್ಟು?",
    "phone number": "ಫೋನ್ ನಂಬರ್",
    "nantara nanage kare maadi": "ನಂತರ ನನಗೆ ಕರೆ ಮಾಡಿ",
    "nantara kare maadi": "ನಂತರ ಕರೆ ಮಾಡಿ",
    "kare maadi": "ಕರೆ ಮಾಡಿ",
    "phone maadi": "ಫೋನ್ ಮಾಡಿ",
    "phone maadtini": "ಫೋನ್ ಮಾಡ್ತೀನಿ",
    "halo. nanna hesaru prayank": "ಹಲೋ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "halo. nanna hesaru prayank.": "ಹಲೋ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "sari. yaaru maatadtiddira": "ಸರಿ. ಯಾರು ಮಾತಾಡ್ತಿದ್ದೀರಾ",
    "sari. yaaru maatadtiddira?": "ಸರಿ. ಯಾರು ಮಾತಾಡ್ತಿದ್ದೀರಾ?",
    "nanna hesaru prayank. nanage kare maadi — swalpa help beku": (
        "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ನನಗೆ ಕರೆ ಮಾಡಿ. ಸ್ವಲ್ಪ ಹೆಲ್ಪ್ ಬೇಕು"
    ),
    "nanna hesaru prayank. nanage kare maadi - swalpa help beku": (
        "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ನನಗೆ ಕರೆ ಮಾಡಿ. ಸ್ವಲ್ಪ ಹೆಲ್ಪ್ ಬೇಕು"
    ),
    "nanna hesaru prayank. nanage kare maadi. swalpa help beku": (
        "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ನನಗೆ ಕರೆ ಮಾಡಿ. ಸ್ವಲ್ಪ ಹೆಲ್ಪ್ ಬೇಕು"
    ),
    "swalpa help beku": "ಸ್ವಲ್ಪ ಹೆಲ್ಪ್ ಬೇಕು",
    "help beku": "ಹೆಲ್ಪ್ ಬೇಕು",
    "sari. ondu nimisha kaayri": "ಸರಿ. ಒಂದು ನಿಮಿಷ ಕಾಯ್ರಿ",
    "sari. ondu nimisha kaayri.": "ಸರಿ. ಒಂದು ನಿಮಿಷ ಕಾಯ್ರಿ",
    "sari. dhanyavadagalu": "ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "sari. dhanyavadagalu.": "ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "halo. ravi avaru iddara": "ಹಲೋ. ರವಿ ಅವರು ಇದ್ದಾರಾ",
    "halo. ravi avaru iddara?": "ಹಲೋ. ರವಿ ಅವರು ಇದ್ದಾರಾ?",
    "ravi avaru iddara": "ರವಿ ಅವರು ಇದ್ದಾರಾ",
    "ravi avaru iddara?": "ರವಿ ಅವರು ಇದ್ದಾರಾ?",
    "avaru iddara": "ಅವರು ಇದ್ದಾರಾ",
    "avaru iddara?": "ಅವರು ಇದ್ದಾರಾ?",
    "sari. nantara nanage kare maadi. nimma phone number eshtu": (
        "ಸರಿ. ನಂತರ ನನಗೆ ಕರೆ ಮಾಡಿ. ನಿಮ್ಮ ಫೋನ್ ನಂಬರ್ ಎಷ್ಟು"
    ),
    "sari. nantara nanage kare maadi. nimma phone number eshtu?": (
        "ಸರಿ. ನಂತರ ನನಗೆ ಕರೆ ಮಾಡಿ. ನಿಮ್ಮ ಫೋನ್ ನಂಬರ್ ಎಷ್ಟು?"
    ),
    "sari. naanu phone maadtini": "ಸರಿ. ನಾನು ಫೋನ್ ಮಾಡ್ತೀನಿ",
    "sari. naanu phone maadtini.": "ಸರಿ. ನಾನು ಫೋನ್ ಮಾಡ್ತೀನಿ",
    "maatadu / maatadtiddira": "ಮಾತಾಡು",
    "call me": "ನನಗೆ ಕರೆ ಮಾಡಿ",
    # L11 society staff
    "flat": "ಫ್ಲಾಟ್",
    "flat 302": "ಫ್ಲಾಟ್ 302",
    "nanna hesaru prayank. flat 302": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ಫ್ಲಾಟ್ 302",
    "nanna hesaru prayank. flat 302.": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ಫ್ಲಾಟ್ 302",
    "guest": "ಗೆಸ್ಟ್",
    "friend": "ಫ್ರೆಂಡ್",
    "barthidare": "ಬರ್ತಿದ್ದಾರೆ",
    "guest barthidare": "ಗೆಸ್ಟ್ ಬರ್ತಿದ್ದಾರೆ",
    "friend barthidare": "ಫ್ರೆಂಡ್ ಬರ್ತಿದ್ದಾರೆ",
    "parcel": "ಪಾರ್ಸೆಲ್",
    "parcel ide na": "ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ",
    "parcel ide na?": "ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ?",
    "amazon parcel": "ಅಮೆಜಾನ್ ಪಾರ್ಸೆಲ್",
    "amazon parcel ide na": "ಅಮೆಜಾನ್ ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ",
    "amazon parcel ide na?": "ಅಮೆಜಾನ್ ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ?",
    "nanna flat-ge": "ನನ್ನ ಫ್ಲಾಟ್‌ಗೆ",
    "flat-ge": "ಫ್ಲಾಟ್‌ಗೆ",
    "nanna flat-ge kodri": "ನನ್ನ ಫ್ಲಾಟ್‌ಗೆ ಕೊಡ್ರಿ",
    "mele": "ಮೇಲೆ",
    "kelage": "ಕೆಳಗೆ",
    "mele hogi": "ಮೇಲೆ ಹೋಗಿ",
    "bandide": "ಬಂದಿದೆ",
    "soft aagilla": "ಸಾಫ್ಟ್ ಆಗಿಲ್ಲ",
    "dayavittu door open maadi": "ದಯವಿಟ್ಟು ಡೋರ್ ಓಪನ್ ಮಾಡಿ",
    "key beku": "ಕೀ ಬೇಕು",
    "key": "ಕೀ",
    "lift": "ಲಿಫ್ಟ್",
    "lift elli ide": "ಲಿಫ್ಟ್ ಎಲ್ಲಿ ಇದೆ",
    "lift elli ide?": "ಲಿಫ್ಟ್ ಎಲ್ಲಿ ಇದೆ?",
    "sari, thank you": "ಸರಿ, ಥ್ಯಾಂಕ್ ಯೂ",
    "tumba help aytu": "ತುಂಬಾ ಹೆಲ್ಪ್ ಆಯ್ತು",
    "help aytu": "ಹೆಲ್ಪ್ ಆಯ್ತು",
    "yaaru": "ಯಾರು",
    "yaaru?": "ಯಾರು?",
    "namaskara. yaaru": "ನಮಸ್ಕಾರ. ಯಾರು",
    "namaskara. yaaru?": "ನಮಸ್ಕಾರ. ಯಾರು?",
    "sari, hogi": "ಸರಿ, ಹೋಗಿ",
    "sari, hogi.": "ಸರಿ, ಹೋಗಿ",
    "kshamisi. amazon parcel ide na": "ಕ್ಷಮಿಸಿ. ಅಮೆಜಾನ್ ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ",
    "kshamisi. amazon parcel ide na?": "ಕ್ಷಮಿಸಿ. ಅಮೆಜಾನ್ ಪಾರ್ಸೆಲ್ ಇದೆ ನಾ?",
    "haudu. nimma hesaru": "ಹೌದು. ನಿಮ್ಮ ಹೆಸರು",
    "haudu. nimma hesaru?": "ಹೌದು. ನಿಮ್ಮ ಹೆಸರು?",
    "prayank. nanna flat-ge kodri. mele hogi — 302": (
        "ಪ್ರಯಾಂಕ್. ನನ್ನ ಫ್ಲಾಟ್‌ಗೆ ಕೊಡ್ರಿ. ಮೇಲೆ ಹೋಗಿ — 302"
    ),
    "prayank. nanna flat-ge kodri. mele hogi — 302.": (
        "ಪ್ರಯಾಂಕ್. ನನ್ನ ಫ್ಲಾಟ್‌ಗೆ ಕೊಡ್ರಿ. ಮೇಲೆ ಹೋಗಿ — 302"
    ),
    "tumba help aytu. dhanyavadagalu": "ತುಂಬಾ ಹೆಲ್ಪ್ ಆಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "tumba help aytu. dhanyavadagalu.": "ತುಂಬಾ ಹೆಲ್ಪ್ ಆಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "guest barthidare. nanage kare maadi": "ಗೆಸ್ಟ್ ಬರ್ತಿದ್ದಾರೆ. ನನಗೆ ಕರೆ ಮಾಡಿ",
    "guest barthidare. nanage kare maadi.": "ಗೆಸ್ಟ್ ಬರ್ತಿದ್ದಾರೆ. ನನಗೆ ಕರೆ ಮಾಡಿ",
    "water can": "ವಾಟರ್ ಕ್ಯಾನ್",
    "garbage": "ಗಾರ್ಬೇಜ್",
    "parking": "ಪಾರ್ಕಿಂಗ್",
    # L12 weather small talk
    "bisi": "ಬಿಸಿ",
    "male": "ಮಳೆ",
    "hottu": "ಹೊತ್ತು",
    "mabbu": "ಮಬ್ಬು",
    "thandi": "ತಣ್ಣಿ",
    "chali": "ಚಳಿ",
    "thandi / chali": "ತಣ್ಣಿ",
    "climate": "ಕ್ಲೈಮೇಟ್",
    "traffic": "ಟ್ರಾಫಿಕ್",
    "umbrella": "ಅಂಬ್ರೆಲ್ಲಾ",
    "bartha ide": "ಬರ್ತಾ ಇದೆ",
    "male bartha ide": "ಮಳೆ ಬರ್ತಾ ಇದೆ",
    "male bandide": "ಮಳೆ ಬಂದಿದೆ",
    "male bartha ide · male bandide": "ಮಳೆ ಬರ್ತಾ ಇದೆ. ಮಳೆ ಬಂದಿದೆ",
    "ivattu tumba bisi": "ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ",
    "hottu jaasti": "ಹೊತ್ತು ಜಾಸ್ತಿ",
    "mabbu ide": "ಮಬ್ಬು ಇದೆ",
    "hottu jaasti · mabbu ide": "ಹೊತ್ತು ಜಾಸ್ತಿ. ಮಬ್ಬು ಇದೆ",
    "swalpa thandi ide": "ಸ್ವಲ್ಪ ತಣ್ಣಿ ಇದೆ",
    "chali bartha ide": "ಚಳಿ ಬರ್ತಾ ಇದೆ",
    "swalpa thandi ide · chali bartha ide": "ಸ್ವಲ್ಪ ತಣ್ಣಿ ಇದೆ. ಚಳಿ ಬರ್ತಾ ಇದೆ",
    "traffic jaasti": "ಟ್ರಾಫಿಕ್ ಜಾಸ್ತಿ",
    "road block ide": "ರೋಡ್ ಬ್ಲಾಕ್ ಇದೆ",
    "traffic jaasti · road block ide": "ಟ್ರಾಫಿಕ್ ಜಾಸ್ತಿ. ರೋಡ್ ಬ್ಲಾಕ್ ಇದೆ",
    "olle climate": "ಒಳ್ಳೆ ಕ್ಲೈಮೇಟ್",
    "olle climate ivattu": "ಒಳ್ಳೆ ಕ್ಲೈಮೇಟ್ ಇವತ್ತು",
    "fresh ide": "ಫ್ರೆಶ್ ಇದೆ",
    "olle climate ivattu · fresh ide": "ಒಳ್ಳೆ ಕ್ಲೈಮೇಟ್ ಇವತ್ತು. ಫ್ರೆಶ್ ಇದೆ",
    "umba": "ಅಲ್ವಾ",
    "sari na": "ಸರಿ ನಾ",
    "sari na?": "ಸರಿ ನಾ?",
    "umba / sari na": "ಸರಿ ನಾ",
    "umba / sari na?": "ಸರಿ ನಾ?",
    "haudu sari": "ಹೌದು ಸರಿ",
    "nantara male barabahudu": "ನಂತರ ಮಳೆ ಬರಬಹುದು",
    "umbrella beku": "ಅಂಬ್ರೆಲ್ಲಾ ಬೇಕು",
    "nantara male barabahudu · umbrella beku": "ನಂತರ ಮಳೆ ಬರಬಹುದು. ಅಂಬ್ರೆಲ್ಲಾ ಬೇಕು",
    "barabahudu": "ಬರಬಹುದು",
    "chennagidini. ivattu tumba bisi, sari na": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ, ಸರಿ ನಾ",
    "chennagidini. ivattu tumba bisi, sari na?": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ, ಸರಿ ನಾ?",
    "haudu. male bartha ide anta": "ಹೌದು. ಮಳೆ ಬರ್ತಾ ಇದೆ ಅಂತ",
    "haudu. male bartha ide anta.": "ಹೌದು. ಮಳೆ ಬರ್ತಾ ಇದೆ ಅಂತ",
    "sari. olle dinagalu": "ಸರಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "sari. olle dinagalu.": "ಸರಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "male bandide! traffic jaasti": "ಮಳೆ ಬಂದಿದೆ! ಟ್ರಾಫಿಕ್ ಜಾಸ್ತಿ",
    "male bandide! traffic jaasti.": "ಮಳೆ ಬಂದಿದೆ! ಟ್ರಾಫಿಕ್ ಜಾಸ್ತಿ",
    "haudu sir. careful": "ಹೌದು ಸರ್. ಕೇರ್ಫುಲ್",
    "haudu sir. careful.": "ಹೌದು ಸರ್. ಕೇರ್ಫುಲ್",
    "anta": "ಅಂತ",
    # L13 auto ride
    "hogona": "ಹೋಗೋಣ",
    "gotha": "ಗೊತ್ತಾ",
    "gotha?": "ಗೊತ್ತಾ?",
    "nilsi": "ನಿಲ್ಸಿ",
    "bilisi": "ಬಿಡ್ಸಿ",
    "illi nilsi": "ಇಲ್ಲಿ ನಿಲ್ಸಿ",
    "iggade bilisi": "ಇಗ್ಗಡೆ ಬಿಡ್ಸಿ",
    "map nodri": "ಮ್ಯಾಪ್ ನೋಡ್ರಿ",
    "map": "ಮ್ಯಾಪ್",
    "nodri": "ನೋಡ್ರಿ",
    "innondu": "ಇನ್ನೊಂದು",
    "road": "ರೋಡ್",
    "innondu road hogi": "ಇನ್ನೊಂದು ರೋಡ್ ಹೋಗಿ",
    "idhu correct alla": "ಇದು ಕರೆಕ್ಟ್ ಅಲ್ಲ",
    "correct alla": "ಕರೆಕ್ಟ್ ಅಲ್ಲ",
    "correct": "ಕರೆಕ್ಟ್",
    "indiranagar-ge hogona": "ಇಂದಿರಾನಗರಕ್ಕೆ ಹೋಗೋಣ",
    "koramangala-ge hogona": "ಕೋರಮಂಗಲಕ್ಕೆ ಹೋಗೋಣ",
    "gate hattira": "ಗೇಟ್ ಹತ್ತಿರ",
    "left side": "ಲೆಫ್ಟ್ ಸೈಡ್",
    "right side": "ರೈಟ್ ಸೈಡ್",
    "change": "ಚೇಂಜ್",
    "change ide na": "ಚೇಂಜ್ ಇದೆ ನಾ",
    "change ide na?": "ಚೇಂಜ್ ಇದೆ ನಾ?",
    "keep change": "ಕೀಪ್ ಚೇಂಜ್",
    "illi sari": "ಇಲ್ಲಿ ಸರಿ",
    "illi sari · eshtu aytu": "ಇಲ್ಲಿ ಸರಿ. ಎಷ್ಟು ಆಯ್ತು",
    "illi sari · eshtu aytu?": "ಇಲ್ಲಿ ಸರಿ. ಎಷ್ಟು ಆಯ್ತು?",
    "gotha? · map nodri": "ಗೊತ್ತಾ? ಮ್ಯಾಪ್ ನೋಡ್ರಿ",
    "illi nilsi · iggade bilisi": "ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಇಗ್ಗಡೆ ಬಿಡ್ಸಿ",
    "idhu correct alla · innondu road hogi": "ಇದು ಕರೆಕ್ಟ್ ಅಲ್ಲ. ಇನ್ನೊಂದು ರೋಡ್ ಹೋಗಿ",
    "namaskara. koramangala-ge hogona. meter haki": "ನಮಸ್ಕಾರ. ಕೋರಮಂಗಲಕ್ಕೆ ಹೋಗೋಣ. ಮೀಟರ್ ಹಾಕಿ",
    "namaskara. koramangala-ge hogona. meter haki.": "ನಮಸ್ಕಾರ. ಕೋರಮಂಗಲಕ್ಕೆ ಹೋಗೋಣ. ಮೀಟರ್ ಹಾಕಿ",
    "sari. gotha": "ಸರಿ. ಗೊತ್ತಾ",
    "sari. gotha.": "ಸರಿ. ಗೊತ್ತಾ",
    "swalpa eduru… nantara balakke. gate hattira": "ಸ್ವಲ್ಪ ಎದುರು. ನಂತರ ಬಲಕ್ಕೆ. ಗೇಟ್ ಹತ್ತಿರ",
    "swalpa eduru. nantara balakke. gate hattira": "ಸ್ವಲ್ಪ ಎದುರು. ನಂತರ ಬಲಕ್ಕೆ. ಗೇಟ್ ಹತ್ತಿರ",
    "swalpa eduru… nantara balakke. gate hattira.": "ಸ್ವಲ್ಪ ಎದುರು. ನಂತರ ಬಲಕ್ಕೆ. ಗೇಟ್ ಹತ್ತಿರ",
    "illi na": "ಇಲ್ಲಿ ನಾ",
    "illi na?": "ಇಲ್ಲಿ ನಾ?",
    "haudu. illi nilsi. iggade bilisi": "ಹೌದು. ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಇಗ್ಗಡೆ ಬಿಡ್ಸಿ",
    "haudu. illi nilsi. iggade bilisi.": "ಹೌದು. ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಇಗ್ಗಡೆ ಬಿಡ್ಸಿ",
    "incorrect route": "ತಪ್ಪು ರಸ್ತೆ",
    "wrong road": "ರಾಂಗ್ ರೋಡ್",
    "swalpa eduru": "ಸ್ವಲ್ಪ ಎದುರು",
    "nantara balakke": "ನಂತರ ಬಲಕ್ಕೆ",
    "swalpa eduru · nantara balakke": "ಸ್ವಲ್ಪ ಎದುರು. ನಂತರ ಬಲಕ್ಕೆ",
    # L14 minutes past hour
    "kaalu": "ಕಾಲು",
    "munche": "ಮುಂಚೆ",
    "aaytu": "ಆಯ್ತು",
    "aidu gante kaalu": "ಐದು ಗಂಟೆ ಕಾಲು",
    "aidu gante hattu nimisha": "ಐದು ಗಂಟೆ ಹತ್ತು ನಿಮಿಷ",
    "hattu gante ippatthu nimisha": "ಹತ್ತು ಗಂಟೆ ಇಪ್ಪತ್ತು ನಿಮಿಷ",
    "elu gante-ge munche": "ಏಳು ಗಂಟೆಗೆ ಮುಂಚೆ",
    "elu gante-ge nantara": "ಏಳು ಗಂಟೆಗೆ ನಂತರ",
    "elu gante aaytu": "ಏಳು ಗಂಟೆ ಆಯ್ತು",
    "elu gante-ge nantara · elu gante aaytu": "ಏಳು ಗಂಟೆಗೆ ನಂತರ. ಏಳು ಗಂಟೆ ಆಯ್ತು",
    "swalpa late aytu · aidu nimisha late": "ಸ್ವಲ್ಪ ಲೇಟ್ ಆಯ್ತು. ಐದು ನಿಮಿಷ ಲೇಟ್",
    "aidu nimisha late": "ಐದು ನಿಮಿಷ ಲೇಟ್",
    "swalpa late aytu": "ಸ್ವಲ್ಪ ಲೇಟ್ ಆಯ್ತು",
    "time sari ide": "ಟೈಮ್ ಸರಿ ಇದೆ",
    "innu hattu nimisha ide": "ಇನ್ನೂ ಹತ್ತು ನಿಮಿಷ ಇದೆ",
    "time sari ide · innu hattu nimisha ide": "ಟೈಮ್ ಸರಿ ಇದೆ. ಇನ್ನೂ ಹತ್ತು ನಿಮಿಷ ಇದೆ",
    "yaavaaga start": "ಯಾವಾಗ ಸ್ಟಾರ್ಟ್",
    "yaavaaga start?": "ಯಾವಾಗ ಸ್ಟಾರ್ಟ್?",
    "hattu gante kaalu-ge": "ಹತ್ತು ಗಂಟೆ ಕಾಲುಗೆ",
    "yaavaaga start? · hattu gante kaalu-ge": "ಯಾವಾಗ ಸ್ಟಾರ್ಟ್? ಹತ್ತು ಗಂಟೆ ಕಾಲುಗೆ",
    "aidu gante-ge munche": "ಐದು ಗಂಟೆಗೆ ಮುಂಚೆ",
    "aidu gante-ge nantara": "ಐದು ಗಂಟೆಗೆ ನಂತರ",
    "hattu gante kaalu-ge.": "ಹತ್ತು ಗಂಟೆ ಕಾಲುಗೆ",
    "eega eshtu gante": "ಈಗ ಎಷ್ಟು ಗಂಟೆ",
    "eega eshtu gante?": "ಈಗ ಎಷ್ಟು ಗಂಟೆ?",
    "hattu gante. innu hattu nimisha ide": "ಹತ್ತು ಗಂಟೆ. ಇನ್ನೂ ಹತ್ತು ನಿಮಿಷ ಇದೆ",
    "hattu gante. innu hattu nimisha ide.": "ಹತ್ತು ಗಂಟೆ. ಇನ್ನೂ ಹತ್ತು ನಿಮಿಷ ಇದೆ",
    "swalpa late aytu — aidu nimisha": "ಸ್ವಲ್ಪ ಲೇಟ್ ಆಯ್ತು — ಐದು ನಿಮಿಷ",
    "swalpa late aytu — aidu nimisha.": "ಸ್ವಲ್ಪ ಲೇಟ್ ಆಯ್ತು — ಐದು ನಿಮಿಷ",
    "sari sari. elu gante ardha-ge banni": "ಸರಿ ಸರಿ. ಏಳು ಗಂಟೆ ಅರ್ಧಕ್ಕೆ ಬನ್ನಿ",
    "sari sari. elu gante ardha-ge banni.": "ಸರಿ ಸರಿ. ಏಳು ಗಂಟೆ ಅರ್ಧಕ್ಕೆ ಬನ್ನಿ",
    "elu gante ardha-ge banni": "ಏಳು ಗಂಟೆ ಅರ್ಧಕ್ಕೆ ಬನ್ನಿ",
    "sari. gothaytu": "ಸರಿ. ಗೊತ್ತಾಯ್ತು",
    "sari. gothaytu.": "ಸರಿ. ಗೊತ್ತಾಯ್ತು",
    "muvattu nimisha": "ಮೂವತ್ತು ನಿಮಿಷ",
    "aidu gante muvattu nimisha": "ಐದು ಗಂಟೆ ಮೂವತ್ತು ನಿಮಿಷ",
    # L15 review mission glue + long lines
    "aaytu": "ಆಯ್ತು",
    "barthini": "ಬರ್ತೀನಿ",
    "tumba busy": "ತುಂಬಾ ಬಿಜಿ",
    "matte heli": "ಮತ್ತೆ ಹೇಳಿ",
    "heli": "ಹೇಳಿ",
    "matte": "ಮತ್ತೆ",
    "coffee beku na": "ಕಾಫಿ ಬೇಕಾ",
    "coffee beku na?": "ಕಾಫಿ ಬೇಕಾ?",
    "haudu sari": "ಹೌದು ಸರಿ",
    "market-ge hogona": "ಮಾರ್ಕೆಟ್‌ಗೆ ಹೋಗೋಣ",
    "market-ge hogona. meter haki": "ಮಾರ್ಕೆಟ್‌ಗೆ ಹೋಗೋಣ. ಮೀಟರ್ ಹಾಕಿ",
    "swalpa eduru… balakke. illi nilsi. eshtu aytu": "ಸ್ವಲ್ಪ ಎದುರು. ಬಲಕ್ಕೆ. ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಎಷ್ಟು ಆಯ್ತು",
    "swalpa eduru. balakke. illi nilsi. eshtu aytu": "ಸ್ವಲ್ಪ ಎದುರು. ಬಲಕ್ಕೆ. ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಎಷ್ಟು ಆಯ್ತು",
    "swalpa eduru… balakke. illi nilsi. eshtu aytu?": "ಸ್ವಲ್ಪ ಎದುರು. ಬಲಕ್ಕೆ. ಇಲ್ಲಿ ನಿಲ್ಸಿ. ಎಷ್ಟು ಆಯ್ತು?",
    "idhu eshtu? eradu kodri. swalpa kammi maadi": "ಇದು ಎಷ್ಟು? ಎರಡು ಕೊಡ್ರಿ. ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ",
    "sari. bill kodri. … aaytu. manege hogtidini": "ಸರಿ. ಬಿಲ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ",
    "sari. bill kodri. aaytu. manege hogtidini": "ಸರಿ. ಬಿಲ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ",
    "yaavaaga barthini": "ಯಾವಾಗ ಬರ್ತೀನಿ",
    "yaavaaga barthini?": "ಯಾವಾಗ ಬರ್ತೀನಿ?",
    "eega barthini — hattu nimisha": "ಈಗ ಬರ್ತೀನಿ — ಹತ್ತು ನಿಮಿಷ",
    "eega barthini — hattu nimisha.": "ಈಗ ಬರ್ತೀನಿ — ಹತ್ತು ನಿಮಿಷ",
    "halo. nanna hesaru prayank, flat 302. guest barthidare. nanage kare maadi": (
        "ಹಲೋ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್, ಫ್ಲಾಟ್ 302. ಗೆಸ್ಟ್ ಬರ್ತಿದ್ದಾರೆ. ನನಗೆ ಕರೆ ಮಾಡಿ"
    ),
    "halo. nanna hesaru prayank, flat 302. guest barthidare. nanage kare maadi.": (
        "ಹಲೋ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್, ಫ್ಲಾಟ್ 302. ಗೆಸ್ಟ್ ಬರ್ತಿದ್ದಾರೆ. ನನಗೆ ಕರೆ ಮಾಡಿ"
    ),
    "namaskara! hegiddiri? banni": "ನಮಸ್ಕಾರ! ಹೇಗಿದ್ದೀರಿ? ಬನ್ನಿ",
    "namaskara! hegiddiri? banni.": "ನಮಸ್ಕಾರ! ಹೇಗಿದ್ದೀರಿ? ಬನ್ನಿ",
    "chennagidini. ivattu tumba bisi": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ",
    "chennagidini. ivattu tumba bisi!": "ಚೆನ್ನಾಗಿದ್ದೀನಿ. ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ",
    "haudu sari. coffee beku na": "ಹೌದು ಸರಿ. ಕಾಫಿ ಬೇಕಾ",
    "haudu sari. coffee beku na?": "ಹೌದು ಸರಿ. ಕಾಫಿ ಬೇಕಾ?",
    "haudu. dhanyavadagalu": "ಹೌದು. ಧನ್ಯವಾದಗಳು",
    "haudu. dhanyavadagalu.": "ಹೌದು. ಧನ್ಯವಾದಗಳು",
    "eradu kodri": "ಎರಡು ಕೊಡ್ರಿ",
    "hattu rupayi sari": "ಹತ್ತು ರೂಪಾಯಿ ಸರಿ",
    "hattu rupayi sari.": "ಹತ್ತು ರೂಪಾಯಿ ಸರಿ",
    "sari. bill kodri. . aaytu. manege hogtidini": "ಸರಿ. ಬಿಲ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ",
    "sari. bill kodri. aaytu. manege hogtidini.": "ಸರಿ. ಬಿಲ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಮನೆಗೆ ಹೋಗ್ತಿದೀನಿ",
    # L16 shopping quantities
    "kilo": "ಕಿಲೋ",
    "full": "ಫುಲ್",
    "packet": "ಪ್ಯಾಕೆಟ್",
    "piece": "ಪೀಸ್",
    "number": "ನಂಬರ್",
    "bas": "ಬಸ್",
    "weight": "ವೇಟ್",
    "fresh": "ಫ್ರೆಶ್",
    "ardha kilo": "ಅರ್ಧ ಕಿಲೋ",
    "ardha kilo kodri": "ಅರ್ಧ ಕಿಲೋ ಕೊಡ್ರಿ",
    "ondu kilo": "ಒಂದು ಕಿಲೋ",
    "eradu kilo": "ಎರಡು ಕಿಲೋ",
    "ondu kilo · eradu kilo": "ಒಂದು ಕಿಲೋ. ಎರಡು ಕಿಲೋ",
    "ondu packet": "ಒಂದು ಪ್ಯಾಕೆಟ್",
    "eradu packet": "ಎರಡು ಪ್ಯಾಕೆಟ್",
    "ondu packet · eradu packet": "ಒಂದು ಪ್ಯಾಕೆಟ್. ಎರಡು ಪ್ಯಾಕೆಟ್",
    "ondu piece": "ಒಂದು ಪೀಸ್",
    "mooru number": "ಮೂರು ನಂಬರ್",
    "ondu piece · mooru number": "ಒಂದು ಪೀಸ್. ಮೂರು ನಂಬರ್",
    "aaru number": "ಆರು ನಂಬರ್",
    "innu swalpa": "ಇನ್ನೂ ಸ್ವಲ್ಪ",
    "innu swalpa kodri": "ಇನ್ನೂ ಸ್ವಲ್ಪ ಕೊಡ್ರಿ",
    "idhe sari": "ಇದೇ ಸರಿ",
    "idhe sari · bas · aaytu": "ಇದೇ ಸರಿ. ಬಸ್. ಆಯ್ತು",
    "swalpa kammi maadi · weight kammi": "ಸ್ವಲ್ಪ ಕಮ್ಮಿ ಮಾಡಿ. ವೇಟ್ ಕಮ್ಮಿ",
    "weight kammi": "ವೇಟ್ ಕಮ್ಮಿ",
    "fresh ide na": "ಫ್ರೆಶ್ ಇದೆ ನಾ",
    "fresh ide na?": "ಫ್ರೆಶ್ ಇದೆ ನಾ?",
    "chennagi ide na": "ಚೆನ್ನಾಗಿ ಇದೆ ನಾ",
    "chennagi ide na?": "ಚೆನ್ನಾಗಿ ಇದೆ ನಾ?",
    "fresh ide na? · chennagi ide na?": "ಫ್ರೆಶ್ ಇದೆ ನಾ? ಚೆನ್ನಾಗಿ ಇದೆ ನಾ?",
    "chennagi": "ಚೆನ್ನಾಗಿ",
    "namaskara. tomato eshtu": "ನಮಸ್ಕಾರ. ಟೊಮೆಟೊ ಎಷ್ಟು",
    "namaskara. tomato eshtu?": "ನಮಸ್ಕಾರ. ಟೊಮೆಟೊ ಎಷ್ಟು?",
    "tomato eshtu": "ಟೊಮೆಟೊ ಎಷ್ಟು",
    "tomato eshtu?": "ಟೊಮೆಟೊ ಎಷ್ಟು?",
    "hattu rupayi kilo": "ಹತ್ತು ರೂಪಾಯಿ ಕಿಲೋ",
    "hattu rupayi kilo.": "ಹತ್ತು ರೂಪಾಯಿ ಕಿಲೋ",
    "ardha kilo kodri. fresh ide na": "ಅರ್ಧ ಕಿಲೋ ಕೊಡ್ರಿ. ಫ್ರೆಶ್ ಇದೆ ನಾ",
    "ardha kilo kodri. fresh ide na?": "ಅರ್ಧ ಕಿಲೋ ಕೊಡ್ರಿ. ಫ್ರೆಶ್ ಇದೆ ನಾ?",
    "haudu. nodri": "ಹೌದು. ನೋಡ್ರಿ",
    "haudu. nodri.": "ಹೌದು. ನೋಡ್ರಿ",
    "innu swalpa kodri… sari, idhe sari. onion ondu kilo kodri": (
        "ಇನ್ನೂ ಸ್ವಲ್ಪ ಕೊಡ್ರಿ. ಸರಿ, ಇದೇ ಸರಿ. ಈರುಳ್ಳಿ ಒಂದು ಕಿಲೋ ಕೊಡ್ರಿ"
    ),
    "innu swalpa kodri. sari, idhe sari. onion ondu kilo kodri": (
        "ಇನ್ನೂ ಸ್ವಲ್ಪ ಕೊಡ್ರಿ. ಸರಿ, ಇದೇ ಸರಿ. ಈರುಳ್ಳಿ ಒಂದು ಕಿಲೋ ಕೊಡ್ರಿ"
    ),
    "innu swalpa kodri… sari, idhe sari. onion ondu kilo kodri.": (
        "ಇನ್ನೂ ಸ್ವಲ್ಪ ಕೊಡ್ರಿ. ಸರಿ, ಇದೇ ಸರಿ. ಈರುಳ್ಳಿ ಒಂದು ಕಿಲೋ ಕೊಡ್ರಿ"
    ),
    "onion ondu kilo kodri": "ಈರುಳ್ಳಿ ಒಂದು ಕಿಲೋ ಕೊಡ್ರಿ",
    "aaytu. bera eshtu aytu — hadinaidu": "ಆಯ್ತು. ಬೇರೆ ಎಷ್ಟು ಆಯ್ತು — ಹದಿನೈದು",
    "aaytu. bera eshtu aytu — hadinaidu.": "ಆಯ್ತು. ಬೇರೆ ಎಷ್ಟು ಆಯ್ತು — ಹದಿನೈದು",
    "milk eradu packet beku. bread ondu": "ಮಿಲ್ಕ್ ಎರಡು ಪ್ಯಾಕೆಟ್ ಬೇಕು. ಬ್ರೆಡ್ ಒಂದು",
    "milk eradu packet beku. bread ondu.": "ಮಿಲ್ಕ್ ಎರಡು ಪ್ಯಾಕೆಟ್ ಬೇಕು. ಬ್ರೆಡ್ ಒಂದು",
    "sari… ippatthu rupayi": "ಸರಿ. ಇಪ್ಪತ್ತು ರೂಪಾಯಿ",
    "sari… ippatthu rupayi.": "ಸರಿ. ಇಪ್ಪತ್ತು ರೂಪಾಯಿ",
    "sari. ippatthu rupayi": "ಸರಿ. ಇಪ್ಪತ್ತು ರೂಪಾಯಿ",
    "eggs — aaru number kodri. aaytu. bill kodri": "ಎಗ್ಸ್ — ಆರು ನಂಬರ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಬಿಲ್ ಕೊಡ್ರಿ",
    "eggs — aaru number kodri. aaytu. bill kodri.": "ಎಗ್ಸ್ — ಆರು ನಂಬರ್ ಕೊಡ್ರಿ. ಆಯ್ತು. ಬಿಲ್ ಕೊಡ್ರಿ",
    "aaru number kodri": "ಆರು ನಂಬರ್ ಕೊಡ್ರಿ",
    "olle samanya": "ಒಳ್ಳೆ ಸಾಮಾನ್ಯ",
    "khaali packet": "ಖಾಲಿ ಪ್ಯಾಕೆಟ್",
    "olle samanya · khaali packet": "ಒಳ್ಳೆ ಸಾಮಾನ್ಯ. ಖಾಲಿ ಪ್ಯಾಕೆಟ್",
    # L17 pharmacy
    "fever": "ಫೀವರ್",
    "cold": "ಕೋಲ್ಡ್",
    "cough": "ಕಫ್",
    "pain": "ಪೇನ್",
    "medicine": "ಮೆಡಿಸಿನ್",
    "tablet": "ಟ್ಯಾಬ್ಲೆಟ್",
    "prescription": "ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್",
    "doctor": "ಡಾಕ್ಟರ್",
    "kudi": "ಕುಡಿ",
    "tagobeku": "ತಗೊಬೇಕು",
    "nanage fever ide": "ನನಗೆ ಫೀವರ್ ಇದೆ",
    "cold ide": "ಕೋಲ್ಡ್ ಇದೆ",
    "cough ide": "ಕಫ್ ಇದೆ",
    "pain ide": "ಪೇನ್ ಇದೆ",
    "cold ide · cough ide · pain ide": "ಕೋಲ್ಡ್ ಇದೆ. ಕಫ್ ಇದೆ. ಪೇನ್ ಇದೆ",
    "medicine beku": "ಮೆಡಿಸಿನ್ ಬೇಕು",
    "tablet beku": "ಟ್ಯಾಬ್ಲೆಟ್ ಬೇಕು",
    "medicine beku · tablet beku": "ಮೆಡಿಸಿನ್ ಬೇಕು. ಟ್ಯಾಬ್ಲೆಟ್ ಬೇಕು",
    "doctor prescription illa": "ಡಾಕ್ಟರ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಇಲ್ಲ",
    "without prescription sari na": "ವಿದೌಟ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಸರಿ ನಾ",
    "without prescription sari na?": "ವಿದೌಟ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಸರಿ ನಾ?",
    "doctor prescription illa · without prescription sari na": "ಡಾಕ್ಟರ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಇಲ್ಲ. ವಿದೌಟ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಸರಿ ನಾ",
    "doctor prescription illa · without prescription sari na?": "ಡಾಕ್ಟರ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಇಲ್ಲ. ವಿದೌಟ್ ಪ್ರಿಸ್ಕ್ರಿಪ್ಶನ್ ಸರಿ ನಾ?",
    "heghe tagobeku": "ಹೇಗೆ ತಗೊಬೇಕು",
    "heghe tagobeku?": "ಹೇಗೆ ತಗೊಬೇಕು?",
    "after food na": "ಆಫ್ಟರ್ ಫುಡ್ ನಾ",
    "after food na?": "ಆಫ್ಟರ್ ಫುಡ್ ನಾ?",
    "heghe tagobeku? · after food na?": "ಹೇಗೆ ತಗೊಬೇಕು? ಆಫ್ಟರ್ ಫುಡ್ ನಾ?",
    "ondu tablet": "ಒಂದು ಟ್ಯಾಬ್ಲೆಟ್",
    "eradu times": "ಎರಡು ಟೈಮ್ಸ್",
    "moodu days": "ಮೂರು ಡೇಸ್",
    "ondu tablet · eradu times · moodu days": "ಒಂದು ಟ್ಯಾಬ್ಲೆಟ್. ಎರಡು ಟೈಮ್ಸ್. ಮೂರು ಡೇಸ್",
    "side effect ide na": "ಸೈಡ್ ಎಫೆಕ್ಟ್ ಇದೆ ನಾ",
    "side effect ide na?": "ಸೈಡ್ ಎಫೆಕ್ಟ್ ಇದೆ ನಾ?",
    "strong medicine alla na": "ಸ್ಟ್ರಾಂಗ್ ಮೆಡಿಸಿನ್ ಅಲ್ಲ ನಾ",
    "strong medicine alla na?": "ಸ್ಟ್ರಾಂಗ್ ಮೆಡಿಸಿನ್ ಅಲ್ಲ ನಾ?",
    "side effect ide na? · strong medicine alla na?": "ಸೈಡ್ ಎಫೆಕ್ಟ್ ಇದೆ ನಾ? ಸ್ಟ್ರಾಂಗ್ ಮೆಡಿಸಿನ್ ಅಲ್ಲ ನಾ?",
    "neeru jasti kudi": "ನೀರು ಜಾಸ್ತಿ ಕುಡಿ",
    "rest maadi": "ರೆಸ್ಟ್ ಮಾಡಿ",
    "neeru jasti kudi · rest maadi": "ನೀರು ಜಾಸ್ತಿ ಕುಡಿ. ರೆಸ್ಟ್ ಮಾಡಿ",
    "dayavittu idhu kodri": "ದಯವಿಟ್ಟು ಇದು ಕೊಡ್ರಿ",
    "dayavittu idhu kodri · eshtu aytu": "ದಯವಿಟ್ಟು ಇದು ಕೊಡ್ರಿ. ಎಷ್ಟು ಆಯ್ತು",
    "dayavittu idhu kodri · eshtu aytu?": "ದಯವಿಟ್ಟು ಇದು ಕೊಡ್ರಿ. ಎಷ್ಟು ಆಯ್ತು?",
    "namaskara. dayavittu — nanage fever ide, cold ide": "ನಮಸ್ಕಾರ. ದಯವಿಟ್ಟು — ನನಗೆ ಫೀವರ್ ಇದೆ, ಕೋಲ್ಡ್ ಇದೆ",
    "namaskara. dayavittu — nanage fever ide, cold ide.": "ನಮಸ್ಕಾರ. ದಯವಿಟ್ಟು — ನನಗೆ ಫೀವರ್ ಇದೆ, ಕೋಲ್ಡ್ ಇದೆ",
    "doctor nodidira": "ಡಾಕ್ಟರ್ ನೋಡಿದೀರಾ",
    "doctor nodidira?": "ಡಾಕ್ಟರ್ ನೋಡಿದೀರಾ?",
    "illave": "ಇಲ್ಲವೇ",
    "illave. medicine beku — swalpa soft": "ಇಲ್ಲವೇ. ಮೆಡಿಸಿನ್ ಬೇಕು — ಸ್ವಲ್ಪ ಸಾಫ್ಟ್",
    "illave. medicine beku — swalpa soft.": "ಇಲ್ಲವೇ. ಮೆಡಿಸಿನ್ ಬೇಕು — ಸ್ವಲ್ಪ ಸಾಫ್ಟ್",
    "idhu tablet. after food, eradu times": "ಇದು ಟ್ಯಾಬ್ಲೆಟ್. ಆಫ್ಟರ್ ಫುಡ್, ಎರಡು ಟೈಮ್ಸ್",
    "idhu tablet. after food, eradu times.": "ಇದು ಟ್ಯಾಬ್ಲೆಟ್. ಆಫ್ಟರ್ ಫುಡ್, ಎರಡು ಟೈಮ್ಸ್",
    "heghe tagobeku? ondu tablet na": "ಹೇಗೆ ತಗೊಬೇಕು? ಒಂದು ಟ್ಯಾಬ್ಲೆಟ್ ನಾ",
    "heghe tagobeku? ondu tablet na?": "ಹೇಗೆ ತಗೊಬೇಕು? ಒಂದು ಟ್ಯಾಬ್ಲೆಟ್ ನಾ?",
    "haudu. neeru jasti kudi. rest maadi": "ಹೌದು. ನೀರು ಜಾಸ್ತಿ ಕುಡಿ. ರೆಸ್ಟ್ ಮಾಡಿ",
    "haudu. neeru jasti kudi. rest maadi.": "ಹೌದು. ನೀರು ಜಾಸ್ತಿ ಕುಡಿ. ರೆಸ್ಟ್ ಮಾಡಿ",
    "sari. eshtu aytu": "ಸರಿ. ಎಷ್ಟು ಆಯ್ತು",
    "sari. eshtu aytu?": "ಸರಿ. ಎಷ್ಟು ಆಯ್ತು?",
    "jasti": "ಜಾಸ್ತಿ",
    "after food": "ಆಫ್ಟರ್ ಫುಡ್",
    "times": "ಟೈಮ್ಸ್",
    "days": "ಡೇಸ್",
    "moodu": "ಮೂರು",
    # L18 repair talk
    "nidhana": "ನಿಧಾನ",
    "nidhana heli": "ನಿಧಾನ ಹೇಳಿ",
    "swalpa slow heli": "ಸ್ವಲ್ಪ ಸ್ಲೋ ಹೇಳಿ",
    "nidhana heli · swalpa slow heli": "ನಿಧಾನ ಹೇಳಿ. ಸ್ವಲ್ಪ ಸ್ಲೋ ಹೇಳಿ",
    "matte ondu sari heli": "ಮತ್ತೆ ಒಂದು ಸಾರಿ ಹೇಳಿ",
    "matte heli · matte ondu sari heli": "ಮತ್ತೆ ಹೇಳಿ. ಮತ್ತೆ ಒಂದು ಸಾರಿ ಹೇಳಿ",
    "ondu sari": "ಒಂದು ಸಾರಿ",
    "gotthilla": "ಗೊತ್ತಿಲ್ಲ",
    "nanage artha aagilla": "ನನಗೆ ಅರ್ಥ ಆಗಿಲ್ಲ",
    "artha aagilla": "ಅರ್ಥ ಆಗಿಲ್ಲ",
    "gotthilla · nanage artha aagilla": "ಗೊತ್ತಿಲ್ಲ. ನನಗೆ ಅರ್ಥ ಆಗಿಲ್ಲ",
    "english nalli heli": "ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಹೇಳಿ",
    "kannada nalli heli": "ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ",
    "english nalli heli · kannada nalli heli": "ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಹೇಳಿ. ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ",
    "nalli": "ನಲ್ಲಿ",
    "kannada swalpa swalpa barutte": "ಕನ್ನಡ ಸ್ವಲ್ಪ ಸ್ವಲ್ಪ ಬರುತ್ತೆ",
    "idhu eshtu anta": "ಇದು ಎಷ್ಟು ಅಂತ",
    "idhu eshtu anta?": "ಇದು ಎಷ್ಟು ಅಂತ?",
    "yaavaaga anta": "ಯಾವಾಗ ಅಂತ",
    "yaavaaga anta?": "ಯಾವಾಗ ಅಂತ?",
    "idhu eshtu anta? · yaavaaga anta?": "ಇದು ಎಷ್ಟು ಅಂತ? ಯಾವಾಗ ಅಂತ?",
    "sari, gothaytu": "ಸರಿ, ಗೊತ್ತಾಯ್ತು",
    "thanks, clear aytu": "ಥ್ಯಾಂಕ್ಸ್, ಕ್ಲಿಯರ್ ಆಯ್ತು",
    "sari, gothaytu · thanks, clear aytu": "ಸರಿ, ಗೊತ್ತಾಯ್ತು. ಥ್ಯಾಂಕ್ಸ್, ಕ್ಲಿಯರ್ ಆಯ್ತು",
    "clear aytu": "ಕ್ಲಿಯರ್ ಆಯ್ತು",
    "nooru aivattu — cash na card": "ನೂರು ಐವತ್ತು — ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್",
    "nooru aivattu — cash na card?": "ನೂರು ಐವತ್ತು — ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್?",
    "kshamisi — matte heli. nidhana heli": "ಕ್ಷಮಿಸಿ — ಮತ್ತೆ ಹೇಳಿ. ನಿಧಾನ ಹೇಳಿ",
    "kshamisi — matte heli. nidhana heli.": "ಕ್ಷಮಿಸಿ — ಮತ್ತೆ ಹೇಳಿ. ನಿಧಾನ ಹೇಳಿ",
    "nooru… aivattu. cash na card": "ನೂರು. ಐವತ್ತು. ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್",
    "nooru… aivattu. cash na card?": "ನೂರು. ಐವತ್ತು. ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್?",
    "nooru. aivattu. cash na card": "ನೂರು. ಐವತ್ತು. ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್",
    "nooru. aivattu. cash na card?": "ನೂರು. ಐವತ್ತು. ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್?",
    "sari, gothaytu. cash. eshtu aytu? nooru aivattu anta": (
        "ಸರಿ, ಗೊತ್ತಾಯ್ತು. ಕ್ಯಾಶ್. ಎಷ್ಟು ಆಯ್ತು? ನೂರು ಐವತ್ತು ಅಂತ"
    ),
    "sari, gothaytu. cash. eshtu aytu? nooru aivattu anta?": (
        "ಸರಿ, ಗೊತ್ತಾಯ್ತು. ಕ್ಯಾಶ್. ಎಷ್ಟು ಆಯ್ತು? ನೂರು ಐವತ್ತು ಅಂತ?"
    ),
    "sari, gothaytu. cash. nooru aivattu anta": "ಸರಿ, ಗೊತ್ತಾಯ್ತು. ಕ್ಯಾಶ್. ನೂರು ಐವತ್ತು ಅಂತ",
    "sari, gothaytu. cash. nooru aivattu anta?": "ಸರಿ, ಗೊತ್ತಾಯ್ತು. ಕ್ಯಾಶ್. ನೂರು ಐವತ್ತು ಅಂತ?",
    "nooru aivattu anta": "ನೂರು ಐವತ್ತು ಅಂತ",
    "nooru aivattu anta?": "ನೂರು ಐವತ್ತು ಅಂತ?",
    "swalpa slow": "ಸ್ವಲ್ಪ ಸ್ಲೋ",
    "cash na card": "ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್",
    "cash na card?": "ಕ್ಯಾಶ್ ನಾ ಕಾರ್ಡ್?",
    # L19 Karnataka regional food
    "yen": "ಏನ್",
    "special": "ಸ್ಪೆಷಲ್",
    "yen special ide": "ಏನ್ ಸ್ಪೆಷಲ್ ಇದೆ",
    "yen special ide?": "ಏನ್ ಸ್ಪೆಷಲ್ ಇದೆ?",
    "bisi bele bath": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್",
    "bisi bele bath ondu kodri": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ಒಂದು ಕೊಡ್ರಿ",
    "ragi mudde": "ರಾಗಿ ಮುದ್ದೆ",
    "saaru": "ಸಾರು",
    "ragi mudde matte saaru beku": "ರಾಗಿ ಮುದ್ದೆ ಮತ್ತೆ ಸಾರು ಬೇಕು",
    "neer dosa": "ನೀರ್ ದೋಸೆ",
    "akki rotti": "ಅಕ್ಕಿ ರೊಟ್ಟಿ",
    "neer dosa eradu kodri": "ನೀರ್ ದೋಸೆ ಎರಡು ಕೊಡ್ರಿ",
    "akki rotti ondu beku": "ಅಕ್ಕಿ ರೊಟ್ಟಿ ಒಂದು ಬೇಕು",
    "neer dosa eradu kodri · akki rotti ondu beku": "ನೀರ್ ದೋಸೆ ಎರಡು ಕೊಡ್ರಿ. ಅಕ್ಕಿ ರೊಟ್ಟಿ ಒಂದು ಬೇಕು",
    "khara": "ಖಾರ",
    "khara kammi maadi": "ಖಾರ ಕಮ್ಮಿ ಮಾಡಿ",
    "swalpa less spicy": "ಸ್ವಲ್ಪ ಲೆಸ್ ಸ್ಪೈಸಿ",
    "khara kammi maadi · swalpa less spicy": "ಖಾರ ಕಮ್ಮಿ ಮಾಡಿ. ಸ್ವಲ್ಪ ಲೆಸ್ ಸ್ಪೈಸಿ",
    "ishta": "ಇಷ್ಟ",
    "tumba ishta": "ತುಂಬಾ ಇಷ್ಟ",
    "nanage tumba ishta": "ನನಗೆ ತುಂಬಾ ಇಷ್ಟ",
    "olledu": "ಒಳ್ಳೇದು",
    "nanage tumba ishta · olledu": "ನನಗೆ ತುಂಬಾ ಇಷ್ಟ. ಒಳ್ಳೇದು",
    "vangi bath": "ವಾಂಗಿ ಬಾತ್",
    "mysore pak": "ಮೈಸೂರು ಪಾಕ್",
    "vangi bath parcel maadi": "ವಾಂಗಿ ಬಾತ್ ಪಾರ್ಸೆಲ್ ಮಾಡಿ",
    "mysore pak ondu kodri": "ಮೈಸೂರು ಪಾಕ್ ಒಂದು ಕೊಡ್ರಿ",
    "vangi bath parcel maadi · mysore pak ondu kodri": "ವಾಂಗಿ ಬಾತ್ ಪಾರ್ಸೆಲ್ ಮಾಡಿ. ಮೈಸೂರು ಪಾಕ್ ಒಂದು ಕೊಡ್ರಿ",
    "ella": "ಎಲ್ಲಾ",
    "ella ide": "ಎಲ್ಲಾ ಇದೆ",
    "namaskara. yen special ide": "ನಮಸ್ಕಾರ. ಏನ್ ಸ್ಪೆಷಲ್ ಇದೆ",
    "namaskara. yen special ide?": "ನಮಸ್ಕಾರ. ಏನ್ ಸ್ಪೆಷಲ್ ಇದೆ?",
    "bisi bele bath, ragi mudde, neer dosa — ella ide": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್, ರಾಗಿ ಮುದ್ದೆ, ನೀರ್ ದೋಸೆ — ಎಲ್ಲಾ ಇದೆ",
    "bisi bele bath, ragi mudde, neer dosa — ella ide.": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್, ರಾಗಿ ಮುದ್ದೆ, ನೀರ್ ದೋಸೆ — ಎಲ್ಲಾ ಇದೆ",
    "bisi bele bath ondu kodri. khara kammi maadi": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ಒಂದು ಕೊಡ್ರಿ. ಖಾರ ಕಮ್ಮಿ ಮಾಡಿ",
    "bisi bele bath ondu kodri. khara kammi maadi.": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ಒಂದು ಕೊಡ್ರಿ. ಖಾರ ಕಮ್ಮಿ ಮಾಡಿ",
    "sari. iggade na parcel": "ಸರಿ. ಇಗ್ಗಡೆ ನಾ ಪಾರ್ಸೆಲ್",
    "sari. iggade na parcel?": "ಸರಿ. ಇಗ್ಗಡೆ ನಾ ಪಾರ್ಸೆಲ್?",
    "iggade. mysore pak ondu kodri": "ಇಗ್ಗಡೆ. ಮೈಸೂರು ಪಾಕ್ ಒಂದು ಕೊಡ್ರಿ",
    "iggade. mysore pak ondu kodri.": "ಇಗ್ಗಡೆ. ಮೈಸೂರು ಪಾಕ್ ಒಂದು ಕೊಡ್ರಿ",
    "olledu — nanage tumba ishta. bill kodri": "ಒಳ್ಳೇದು — ನನಗೆ ತುಂಬಾ ಇಷ್ಟ. ಬಿಲ್ ಕೊಡ್ರಿ",
    "olledu — nanage tumba ishta. bill kodri.": "ಒಳ್ಳೇದು — ನನಗೆ ತುಂಬಾ ಇಷ್ಟ. ಬಿಲ್ ಕೊಡ್ರಿ",
    "sari. iggade na": "ಸರಿ. ಇಗ್ಗಡೆ ನಾ",
    "sari. iggade na?": "ಸರಿ. ಇಗ್ಗಡೆ ನಾ?",
    "sari. dhanyavadagalu": "ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "sari. dhanyavadagalu!": "ಸರಿ. ಧನ್ಯವಾದಗಳು",
    # L20 Karnataka regions & cities
    "ooru": "ಊರು",
    "ellinda": "ಎಲ್ಲಿಂದ",
    "ellinda?": "ಎಲ್ಲಿಂದ?",
    "neevu ellinda": "ನೀವು ಎಲ್ಲಿಂದ",
    "neevu ellinda?": "ನೀವು ಎಲ್ಲಿಂದ?",
    "nimma ooru": "ನಿಮ್ಮ ಊರು",
    "nimma ooru elli": "ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ",
    "nimma ooru elli?": "ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ?",
    "nanna ooru": "ನನ್ನ ಊರು",
    "nanna ooru bengaluru": "ನನ್ನ ಊರು ಬೆಂಗಳೂರು",
    "nanna ooru mysuru": "ನನ್ನ ಊರು ಮೈಸೂರು",
    "nanna ooru mangaluru": "ನನ್ನ ಊರು ಮಂಗಳೂರು",
    "nanna ooru hubballi": "ನನ್ನ ಊರು ಹುಬ್ಬಳ್ಳಿ",
    "yaava": "ಯಾವ",
    "yaava ooru": "ಯಾವ ಊರು",
    "yaava ooru?": "ಯಾವ ಊರು?",
    "inda": "ಇಂದ",
    "-inda": "ಇಂದ",
    "bengaluru": "ಬೆಂಗಳೂರು",
    "mysuru": "ಮೈಸೂರು",
    "mangaluru": "ಮಂಗಳೂರು",
    "udupi": "ಉಡುಪಿ",
    "hubballi": "ಹುಬ್ಬಳ್ಳಿ",
    "belagavi": "ಬೆಳಗಾವಿ",
    "kalaburagi": "ಕಲಬುರಗಿ",
    "kodagu": "ಕೊಡಗು",
    "karnataka": "ಕರ್ನಾಟಕ",
    "karavali": "ಕರಾವಳಿ",
    "malenadu": "ಮಲೆನಾಡು",
    "uttara karnataka": "ಉತ್ತರ ಕರ್ನಾಟಕ",
    "karavali · malenadu · uttara karnataka": "ಕರಾವಳಿ. ಮಲೆನಾಡು. ಉತ್ತರ ಕರ್ನಾಟಕ",
    "mysuru-inda": "ಮೈಸೂರಿಂದ",
    "mangaluru-inda": "ಮಂಗಳೂರಿಂದ",
    "bengaluru-inda": "ಬೆಂಗಳೂರಿಂದ",
    "hubballi-inda": "ಹುಬ್ಬಳ್ಳಿಯಿಂದ",
    "belagavi-inda": "ಬೆಳಗಾವಿಯಿಂದ",
    "naanu mysuru-inda": "ನಾನು ಮೈಸೂರಿಂದ",
    "naanu mangaluru-inda": "ನಾನು ಮಂಗಳೂರಿಂದ",
    "naanu mysuru-inda · naanu mangaluru-inda": "ನಾನು ಮೈಸೂರಿಂದ. ನಾನು ಮಂಗಳೂರಿಂದ",
    "naanu hubballi-inda": "ನಾನು ಹುಬ್ಬಳ್ಳಿಯಿಂದ",
    "naanu bengaluru-inda": "ನಾನು ಬೆಂಗಳೂರಿಂದ",
    "bengaluru-alli": "ಬೆಂಗಳೂರಲ್ಲಿ",
    "iddini": "ಇದ್ದೀನಿ",
    "naanu bengaluru-alli iddini": "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ",
    "illi kelasa": "ಇಲ್ಲಿ ಕೆಲಸ",
    "naanu bengaluru-alli iddini · illi kelasa": "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ. ಇಲ್ಲಿ ಕೆಲಸ",
    "namaskara. neevu ellinda": "ನಮಸ್ಕಾರ. ನೀವು ಎಲ್ಲಿಂದ",
    "namaskara. neevu ellinda?": "ನಮಸ್ಕಾರ. ನೀವು ಎಲ್ಲಿಂದ?",
    "namaskara. nanna ooru bengaluru. nimma ooru elli": "ನಮಸ್ಕಾರ. ನನ್ನ ಊರು ಬೆಂಗಳೂರು. ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ",
    "namaskara. nanna ooru bengaluru. nimma ooru elli?": "ನಮಸ್ಕಾರ. ನನ್ನ ಊರು ಬೆಂಗಳೂರು. ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ?",
    "nanna ooru bengaluru. nimma ooru elli": "ನನ್ನ ಊರು ಬೆಂಗಳೂರು. ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ",
    "nanna ooru bengaluru. nimma ooru elli?": "ನನ್ನ ಊರು ಬೆಂಗಳೂರು. ನಿಮ್ಮ ಊರು ಎಲ್ಲಿ?",
    "naanu mangaluru-inda. karavali": "ನಾನು ಮಂಗಳೂರಿಂದ. ಕರಾವಳಿ",
    "naanu mangaluru-inda. karavali.": "ನಾನು ಮಂಗಳೂರಿಂದ. ಕರಾವಳಿ",
    "sari. yaava ooru — mangaluru na udupi": "ಸರಿ. ಯಾವ ಊರು — ಮಂಗಳೂರು ನಾ ಉಡುಪಿ",
    "sari. yaava ooru — mangaluru na udupi?": "ಸರಿ. ಯಾವ ಊರು — ಮಂಗಳೂರು ನಾ ಉಡುಪಿ?",
    "mangaluru. neevu illi kelasa na": "ಮಂಗಳೂರು. ನೀವು ಇಲ್ಲಿ ಕೆಲಸ ನಾ",
    "mangaluru. neevu illi kelasa na?": "ಮಂಗಳೂರು. ನೀವು ಇಲ್ಲಿ ಕೆಲಸ ನಾ?",
    "illi kelasa na": "ಇಲ್ಲಿ ಕೆಲಸ ನಾ",
    "illi kelasa na?": "ಇಲ್ಲಿ ಕೆಲಸ ನಾ?",
    "haudu. naanu bengaluru-alli iddini. olle dinagalu": "ಹೌದು. ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "haudu. naanu bengaluru-alli iddini. olle dinagalu!": "ಹೌದು. ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "haudu. bengaluru-alli iddini. olle dinagalu": "ಹೌದು. ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "haudu. bengaluru-alli iddini. olle dinagalu!": "ಹೌದು. ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "bengaluru-alli iddini": "ಬೆಂಗಳೂರಲ್ಲಿ ಇದ್ದೀನಿ",
    "mangaluru. illi kelasa na": "ಮಂಗಳೂರು. ಇಲ್ಲಿ ಕೆಲಸ ನಾ",
    "mangaluru. illi kelasa na?": "ಮಂಗಳೂರು. ಇಲ್ಲಿ ಕೆಲಸ ನಾ?",
    # L21 hotel check-in
    "khali": "ಖಾಲಿ",
    "ideya": "ಇದೆಯಾ",
    "ideya?": "ಇದೆಯಾ?",
    "khali room ideya": "ಖಾಲಿ ರೂಮ್ ಇದೆಯಾ",
    "khali room ideya?": "ಖಾಲಿ ರೂಮ್ ಇದೆಯಾ?",
    "room": "ರೂಮ್",
    "lodge": "ಲಾಡ್ಜ್",
    "booking": "ಬುಕಿಂಗ್",
    "raatri": "ರಾತ್ರಿ",
    "baadige": "ಬಾಡಿಗೆ",
    "key": "ಕೀ",
    "check-in": "ಚೆಕ್-ಇನ್",
    "check-out": "ಚೆಕ್-ಔಟ್",
    "single": "ಸಿಂಗಲ್",
    "double": "ಡಬಲ್",
    "wifi": "ವೈಫೈ",
    "password": "ಪಾಸ್‌ವರ್ಡ್",
    "ondu room beku": "ಒಂದು ರೂಮ್ ಬೇಕು",
    "ondu raatri beku": "ಒಂದು ರಾತ್ರಿ ಬೇಕು",
    "eradu raatri": "ಎರಡು ರಾತ್ರಿ",
    "eradu raatri beku": "ಎರಡು ರಾತ್ರಿ ಬೇಕು",
    "ondu room beku · ondu raatri beku": "ಒಂದು ರೂಮ್ ಬೇಕು. ಒಂದು ರಾತ್ರಿ ಬೇಕು",
    "nanna booking ide": "ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ",
    "nanna booking ide · nanna hesaru prayank": "ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "room eshtu": "ರೂಮ್ ಎಷ್ಟು",
    "room eshtu?": "ರೂಮ್ ಎಷ್ಟು?",
    "ondu raatri-ge": "ಒಂದು ರಾತ್ರಿಗೆ",
    "ondu raatri-ge eshtu": "ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು",
    "ondu raatri-ge eshtu?": "ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು?",
    "room eshtu? · ondu raatri-ge eshtu?": "ರೂಮ್ ಎಷ್ಟು? ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು?",
    "room eshtu · ondu raatri-ge eshtu": "ರೂಮ್ ಎಷ್ಟು. ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು",
    "key kodri": "ಕೀ ಕೊಡ್ರಿ",
    "wifi password heli": "ವೈಫೈ ಪಾಸ್‌ವರ್ಡ್ ಹೇಳಿ",
    "key kodri · wifi password heli": "ಕೀ ಕೊಡ್ರಿ. ವೈಫೈ ಪಾಸ್‌ವರ್ಡ್ ಹೇಳಿ",
    "check-out yaavaaga": "ಚೆಕ್-ಔಟ್ ಯಾವಾಗ",
    "check-out yaavaaga?": "ಚೆಕ್-ಔಟ್ ಯಾವಾಗ?",
    "check-out eshtu gante": "ಚೆಕ್-ಔಟ್ ಎಷ್ಟು ಗಂಟೆ",
    "check-out eshtu gante?": "ಚೆಕ್-ಔಟ್ ಎಷ್ಟು ಗಂಟೆ?",
    "check-out yaavaaga? · check-out eshtu gante?": "ಚೆಕ್-ಔಟ್ ಯಾವಾಗ? ಚೆಕ್-ಔಟ್ ಎಷ್ಟು ಗಂಟೆ?",
    "check-out yaavaaga · check-out eshtu gante": "ಚೆಕ್-ಔಟ್ ಯಾವಾಗ. ಚೆಕ್-ಔಟ್ ಎಷ್ಟು ಗಂಟೆ",
    "bill kodri": "ಬಿಲ್ ಕೊಡ್ರಿ",
    "room clean maadi": "ರೂಮ್ ಕ್ಲೀನ್ ಮಾಡಿ",
    "bill kodri · room clean maadi": "ಬಿಲ್ ಕೊಡ್ರಿ. ರೂಮ್ ಕ್ಲೀನ್ ಮಾಡಿ",
    "yaavaaga": "ಯಾವಾಗ",
    "yaavaaga?": "ಯಾವಾಗ?",
    "heli": "ಹೇಳಿ",
    "helutini": "ಹೇಳ್ತೀನಿ",
    "savira": "ಸಾವಿರ",
    "eradu savira": "ಎರಡು ಸಾವಿರ",
    "eradu savira rupayi": "ಎರಡು ಸಾವಿರ ರೂಪಾಯಿ",
    "double room": "ಡಬಲ್ ರೂಮ್",
    "single room": "ಸಿಂಗಲ್ ರೂಮ್",
    "double room — eradu savira rupayi": "ಡಬಲ್ ರೂಮ್ — ಎರಡು ಸಾವಿರ ರೂಪಾಯಿ",
    "double room — eradu savira rupayi.": "ಡಬಲ್ ರೂಮ್ — ಎರಡು ಸಾವಿರ ರೂಪಾಯಿ",
    "namaskara. nanna booking ide. nanna hesaru prayank": "ನಮಸ್ಕಾರ. ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "namaskara. nanna booking ide. nanna hesaru prayank.": "ನಮಸ್ಕಾರ. ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ. ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್",
    "sari. ondu raatri na eradu": "ಸರಿ. ಒಂದು ರಾತ್ರಿ ನಾ ಎರಡು",
    "sari. ondu raatri na eradu?": "ಸರಿ. ಒಂದು ರಾತ್ರಿ ನಾ ಎರಡು?",
    "ondu raatri beku. room eshtu": "ಒಂದು ರಾತ್ರಿ ಬೇಕು. ರೂಮ್ ಎಷ್ಟು",
    "ondu raatri beku. room eshtu?": "ಒಂದು ರಾತ್ರಿ ಬೇಕು. ರೂಮ್ ಎಷ್ಟು?",
    "sari. key kodri. wifi password heli": "ಸರಿ. ಕೀ ಕೊಡ್ರಿ. ವೈಫೈ ಪಾಸ್‌ವರ್ಡ್ ಹೇಳಿ",
    "sari. key kodri. wifi password heli.": "ಸರಿ. ಕೀ ಕೊಡ್ರಿ. ವೈಫೈ ಪಾಸ್‌ವರ್ಡ್ ಹೇಳಿ",
    "idhu key": "ಇದು ಕೀ",
    "idhu key. check-out hattu gante": "ಇದು ಕೀ. ಚೆಕ್-ಔಟ್ ಹತ್ತು ಗಂಟೆ",
    "idhu key. check-out hattu gante.": "ಇದು ಕೀ. ಚೆಕ್-ಔಟ್ ಹತ್ತು ಗಂಟೆ",
    "gothaytu. dhanyavadagalu": "ಗೊತ್ತಾಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "gothaytu. dhanyavadagalu!": "ಗೊತ್ತಾಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "namaskara. nanna booking ide": "ನಮಸ್ಕಾರ. ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ",
    "namaskara. nanna booking ide.": "ನಮಸ್ಕಾರ. ನನ್ನ ಬುಕಿಂಗ್ ಇದೆ",
    "sari. nimma hesaru enu": "ಸರಿ. ನಿಮ್ಮ ಹೆಸರು ಏನು",
    "sari. nimma hesaru enu?": "ಸರಿ. ನಿಮ್ಮ ಹೆಸರು ಏನು?",
    "nanna hesaru prayank. ondu raatri beku": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ಒಂದು ರಾತ್ರಿ ಬೇಕು",
    "nanna hesaru prayank. ondu raatri beku.": "ನನ್ನ ಹೆಸರು ಪ್ರಯಾಂಕ್. ಒಂದು ರಾತ್ರಿ ಬೇಕು",
    "double room ide": "ಡಬಲ್ ರೂಮ್ ಇದೆ",
    "double room ide. ondu raatri-ge eshtu helutini": "ಡಬಲ್ ರೂಮ್ ಇದೆ. ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು ಹೇಳ್ತೀನಿ",
    "double room ide. ondu raatri-ge eshtu helutini.": "ಡಬಲ್ ರೂಮ್ ಇದೆ. ಒಂದು ರಾತ್ರಿಗೆ ಎಷ್ಟು ಹೇಳ್ತೀನಿ",
    "gothaytu. beligge bill kodri. dhanyavadagalu": "ಗೊತ್ತಾಯ್ತು. ಬೆಳಿಗ್ಗೆ ಬಿಲ್ ಕೊಡ್ರಿ. ಧನ್ಯವಾದಗಳು",
    "gothaytu. beligge bill kodri. dhanyavadagalu!": "ಗೊತ್ತಾಯ್ತು. ಬೆಳಿಗ್ಗೆ ಬಿಲ್ ಕೊಡ್ರಿ. ಧನ್ಯವಾದಗಳು",
    "sari sari. olle dinagalu": "ಸರಿ ಸರಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "sari sari. olle dinagalu!": "ಸರಿ ಸರಿ. ಒಳ್ಳೆ ದಿನಗಳು",
    "beligge bill kodri": "ಬೆಳಿಗ್ಗೆ ಬಿಲ್ ಕೊಡ್ರಿ",
    "hattu gante": "ಹತ್ತು ಗಂಟೆ",
    # L22 bank / ATM / UPI
    "atm": "ಎಟಿಎಂ",
    "bank": "ಬ್ಯಾಂಕ್",
    "duddu": "ದುಡ್ಡು",
    "rokka": "ರೊಕ್ಕ",
    "cash": "ಕ್ಯಾಶ್",
    "upi": "ಯುಪಿಐ",
    "card": "ಕಾರ್ಡ್",
    "qr": "ಕ್ಯೂಆರ್",
    "scan": "ಸ್ಕ್ಯಾನ್",
    "chiller": "ಚಿಲ್ಲರ್",
    "tagontira": "ತಗೊಣ್ತೀರ",
    "tagontira?": "ತಗೊಣ್ತೀರ?",
    "payment": "ಪೇಮೆಂಟ್",
    "paisa": "ಪೈಸಾ",
    "tegiyona": "ತೆಗಿಯೋಣ",
    "maadtidini": "ಮಾಡ್ತಿದೀನಿ",
    "atm elli ide": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ",
    "atm elli ide?": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ?",
    "bank elli ide": "ಬ್ಯಾಂಕ್ ಎಲ್ಲಿ ಇದೆ",
    "bank elli ide?": "ಬ್ಯಾಂಕ್ ಎಲ್ಲಿ ಇದೆ?",
    "atm elli ide? · bank elli ide?": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ? ಬ್ಯಾಂಕ್ ಎಲ್ಲಿ ಇದೆ?",
    "atm elli ide · bank elli ide": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ. ಬ್ಯಾಂಕ್ ಎಲ್ಲಿ ಇದೆ",
    "nanage cash beku": "ನನಗೆ ಕ್ಯಾಶ್ ಬೇಕು",
    "aivattu savira": "ಐವತ್ತು ಸಾವಿರ",
    "aivattu savira beku": "ಐವತ್ತು ಸಾವಿರ ಬೇಕು",
    "nanage cash beku · aivattu savira beku": "ನನಗೆ ಕ್ಯಾಶ್ ಬೇಕು. ಐವತ್ತು ಸಾವಿರ ಬೇಕು",
    "upi maadi": "ಯುಪಿಐ ಮಾಡಿ",
    "upi ideya": "ಯುಪಿಐ ಇದೆಯಾ",
    "upi ideya?": "ಯುಪಿಐ ಇದೆಯಾ?",
    "upi maadi · upi ideya": "ಯುಪಿಐ ಮಾಡಿ. ಯುಪಿಐ ಇದೆಯಾ",
    "upi maadi · upi ideya?": "ಯುಪಿಐ ಮಾಡಿ. ಯುಪಿಐ ಇದೆಯಾ?",
    "card tagontira": "ಕಾರ್ಡ್ ತಗೊಣ್ತೀರ",
    "card tagontira?": "ಕಾರ್ಡ್ ತಗೊಣ್ತೀರ?",
    "cash na upi": "ಕ್ಯಾಶ್ ನಾ ಯುಪಿಐ",
    "cash na upi?": "ಕ್ಯಾಶ್ ನಾ ಯುಪಿಐ?",
    "card tagontira? · cash na upi?": "ಕಾರ್ಡ್ ತಗೊಣ್ತೀರ? ಕ್ಯಾಶ್ ನಾ ಯುಪಿಐ?",
    "card tagontira · cash na upi": "ಕಾರ್ಡ್ ತಗೊಣ್ತೀರ. ಕ್ಯಾಶ್ ನಾ ಯುಪಿಐ",
    "qr scan maadi": "ಕ್ಯೂಆರ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
    "payment aytu": "ಪೇಮೆಂಟ್ ಆಯ್ತು",
    "qr scan maadi · payment aytu": "ಕ್ಯೂಆರ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ. ಪೇಮೆಂಟ್ ಆಯ್ತು",
    "change kodri": "ಚೇಂಜ್ ಕೊಡ್ರಿ",
    "chiller beku": "ಚಿಲ್ಲರ್ ಬೇಕು",
    "change kodri · chiller beku": "ಚೇಂಜ್ ಕೊಡ್ರಿ. ಚಿಲ್ಲರ್ ಬೇಕು",
    "duddu illa": "ದುಡ್ಡು ಇಲ್ಲ",
    "rokka beku": "ರೊಕ್ಕ ಬೇಕು",
    "duddu illa · rokka beku": "ದುಡ್ಡು ಇಲ್ಲ. ರೊಕ್ಕ ಬೇಕು",
    "eshtu aytu? nooru aivattu": "ಎಷ್ಟು ಆಯ್ತು? ನೂರು ಐವತ್ತು",
    "eshtu aytu? nooru aivattu.": "ಎಷ್ಟು ಆಯ್ತು? ನೂರು ಐವತ್ತು",
    "kshamisi. nanage cash kammi. upi ideya": "ಕ್ಷಮಿಸಿ. ನನಗೆ ಕ್ಯಾಶ್ ಕಮ್ಮಿ. ಯುಪಿಐ ಇದೆಯಾ",
    "kshamisi. nanage cash kammi. upi ideya?": "ಕ್ಷಮಿಸಿ. ನನಗೆ ಕ್ಯಾಶ್ ಕಮ್ಮಿ. ಯುಪಿಐ ಇದೆಯಾ?",
    "nanage cash kammi": "ನನಗೆ ಕ್ಯಾಶ್ ಕಮ್ಮಿ",
    "haudu. qr scan maadi": "ಹೌದು. ಕ್ಯೂಆರ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
    "haudu. qr scan maadi.": "ಹೌದು. ಕ್ಯೂಆರ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
    "sari. upi maadtidini… payment aytu": "ಸರಿ. ಯುಪಿಐ ಮಾಡ್ತಿದೀನಿ. ಪೇಮೆಂಟ್ ಆಯ್ತು",
    "sari. upi maadtidini... payment aytu": "ಸರಿ. ಯುಪಿಐ ಮಾಡ್ತಿದೀನಿ. ಪೇಮೆಂಟ್ ಆಯ್ತು",
    "sari. upi maadtidini. payment aytu": "ಸರಿ. ಯುಪಿಐ ಮಾಡ್ತಿದೀನಿ. ಪೇಮೆಂಟ್ ಆಯ್ತು",
    "upi maadtidini": "ಯುಪಿಐ ಮಾಡ್ತಿದೀನಿ",
    "sari sari. dhanyavadagalu": "ಸರಿ ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "sari sari. dhanyavadagalu.": "ಸರಿ ಸರಿ. ಧನ್ಯವಾದಗಳು",
    "atm elli ide? nantara cash tegiyona": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ? ನಂತರ ಕ್ಯಾಶ್ ತೆಗಿಯೋಣ",
    "atm elli ide? nantara cash tegiyona.": "ಎಟಿಎಂ ಎಲ್ಲಿ ಇದೆ? ನಂತರ ಕ್ಯಾಶ್ ತೆಗಿಯೋಣ",
    "nantara cash tegiyona": "ನಂತರ ಕ್ಯಾಶ್ ತೆಗಿಯೋಣ",
    "eduru bank": "ಎದುರು ಬ್ಯಾಂಕ್",
    "eduru bank. atm alli ide": "ಎದುರು ಬ್ಯಾಂಕ್. ಎಟಿಎಂ ಅಲ್ಲಿ ಇದೆ",
    "eduru bank. atm alli ide.": "ಎದುರು ಬ್ಯಾಂಕ್. ಎಟಿಎಂ ಅಲ್ಲಿ ಇದೆ",
    "atm alli ide": "ಎಟಿಎಂ ಅಲ್ಲಿ ಇದೆ",
    "nooru aivattu aytu": "ನೂರು ಐವತ್ತು ಆಯ್ತು",
    "nooru aivattu aytu.": "ನೂರು ಐವತ್ತು ಆಯ್ತು",
    "payment aytu. dhanyavadagalu": "ಪೇಮೆಂಟ್ ಆಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "payment aytu. dhanyavadagalu.": "ಪೇಮೆಂಟ್ ಆಯ್ತು. ಧನ್ಯವಾದಗಳು",
    "nanage cash beku. aivattu savira": "ನನಗೆ ಕ್ಯಾಶ್ ಬೇಕು. ಐವತ್ತು ಸಾವಿರ",
    "nanage cash beku. aivattu savira.": "ನನಗೆ ಕ್ಯಾಶ್ ಬೇಕು. ಐವತ್ತು ಸಾವಿರ",
    "aaytu. gothaytu": "ಆಯ್ತು. ಗೊತ್ತಾಯ್ತು",
    "aaytu. gothaytu!": "ಆಯ್ತು. ಗೊತ್ತಾಯ್ತು",
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
