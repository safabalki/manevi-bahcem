"""Pixabay'den temaya göre arka plan videosu adaylarını toplar.

Adaylar doğrudan kullanılmaz; insan onayından geçenler arkaplanlar.json'a girer.

Kullanım:  python pixabay.py "sorgu" [adet]
"""
import json
import os
import sys
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent
ADAY_DOSYASI = KOK / "cache" / "pixabay-adaylar.json"

# Etiketinde bunlardan biri geçen klip aday bile olmaz; geri kalanı yine de insan onayından geçer.
YASAK = {
    "person", "people", "man", "men", "woman", "women", "girl", "boy", "child", "children", "kid", "kids", "baby",
    "human", "couple", "family", "friends", "crowd", "tourist", "tourists", "hand", "hands", "face", "portrait",
    "silhouette", "model", "fashion", "bikini", "dance", "dancing", "party", "music", "concert", "guitar",
    "church", "cathedral", "chapel", "cross", "christmas", "jesus", "angel", "buddha", "buddhism", "temple",
    "statue", "idol", "halloween", "wine", "beer", "alcohol", "bar", "cocktail", "cigarette", "smoking",
    "love", "kiss", "wedding", "valentine", "heart", "pig", "flag",
}


def anahtar():
    if os.environ.get("PIXABAY_KEY"):
        return os.environ["PIXABAY_KEY"]
    for satir in (KOK / ".env").read_text(encoding="utf-8").splitlines():
        if satir.startswith("PIXABAY_KEY="):
            return satir.split("=", 1)[1].strip()
    sys.exit("PIXABAY_KEY bulunamadı (.env ya da ortam değişkeni).")


def ara(sorgu, adet=20, en_az_yukseklik=1440, en_az_sure=12):
    r = requests.get("https://pixabay.com/api/videos/", timeout=30, params={
        "key": anahtar(), "q": sorgu, "per_page": max(3, min(adet, 200)),
        "safesearch": "true", "order": "popular",
    })
    r.raise_for_status()
    adaylar = []
    for h in r.json()["hits"]:
        etiketler = {e.strip().lower() for e in h["tags"].split(",")}
        kelimeler = {k for e in etiketler for k in e.split()}
        if kelimeler & YASAK or h["duration"] < en_az_sure:
            continue
        # Dikey kırpmada (16:9'un ortadaki üçte biri) netlik kaybolmasın diye yüksek çözünürlük istiyoruz.
        surum = next((h["videos"][s] for s in ("large", "medium") if h["videos"][s]["height"] >= en_az_yukseklik), None)
        if not surum:
            continue
        adaylar.append({
            "id": h["id"], "sorgu": sorgu, "etiketler": h["tags"], "sure": h["duration"],
            "sayfa": h["pageURL"], "url": surum["url"], "kucuk_resim": h["videos"]["tiny"]["thumbnail"],
            "boyut": f"{surum['width']}x{surum['height']}",
        })
    return adaylar


def indir(aday):
    yol = KOK / "cache" / "pixabay" / f"{aday['id']}.mp4"
    if not yol.exists():
        yol.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(aday["url"], stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(yol, "wb") as f:
                for parca in r.iter_content(1 << 20):
                    f.write(parca)
    return yol


if __name__ == "__main__":
    sorgu = sys.argv[1]
    adet = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    eski = json.loads(ADAY_DOSYASI.read_text(encoding="utf-8")) if ADAY_DOSYASI.exists() else []
    bilinen = {a["id"] for a in eski}
    yeni = [a for a in ara(sorgu, adet) if a["id"] not in bilinen]
    ADAY_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    ADAY_DOSYASI.write_text(json.dumps(eski + yeni, ensure_ascii=False, indent=2), encoding="utf-8")
    for a in yeni:
        print(a["id"], a["boyut"], a["sure"], "sn", a["etiketler"])
