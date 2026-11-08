"""Facebook Sayfasına (Manevi Bahçem) Reels yükler: Graph API video_reels, dosya rupload.facebook.com'a gider.

Token, instagram.py'nin kaydettiği Sayfa token'ıdır (aynı Sayfa); bağlarken `pages_manage_posts` izni verildiyse
token dosyasında "facebook": true olur ve gunluk.py Facebook'a da paylaşır.

Kullanım:
  python facebook.py out/x.mp4      # yanındaki .json'daki açıklamayla Sayfaya Reels olarak paylaş
"""
import json
import sys
import time
from pathlib import Path

import requests

import instagram
from instagram import GRAPH, _cevap


def acik():
    try:
        return bool(instagram.erisim().get("facebook"))
    except Exception:
        return False


def aciklama(bilgi):
    metin = bilgi["aciklama"].replace("#shorts ", "").replace("abone olun", "takip edin")
    return f"{bilgi['baslik']}\n\n{metin} #reels #islam"


def yukle(mp4, bilgi):
    """Reels olarak paylaşır. Dönüş: (video id, bağlantı)."""
    t = instagram.erisim()
    sayfa, token = t["sayfa_id"], t["token"]
    bas = _cevap(requests.post(f"{GRAPH}/{sayfa}/video_reels", timeout=60,
                               data={"upload_phase": "start", "access_token": token}), "fb başlat")
    vid = bas["video_id"]
    boyut = mp4.stat().st_size
    with open(mp4, "rb") as f:
        _cevap(requests.post(bas["upload_url"], data=f, timeout=600, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(boyut)}), "fb yükleme")
    _cevap(requests.post(f"{GRAPH}/{sayfa}/video_reels", timeout=60, data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": aciklama(bilgi), "access_token": token}), "fb yayın")
    for _ in range(60):
        durum = _cevap(requests.get(f"{GRAPH}/{vid}", timeout=60,
                                    params={"fields": "status", "access_token": token}), "fb durum")["status"]
        if durum.get("video_status") in ("ready", "published") or \
                durum.get("publishing_phase", {}).get("status") == "complete":
            break
        if durum.get("video_status") == "error" or durum.get("processing_phase", {}).get("status") == "error":
            raise RuntimeError(f"Facebook videoyu işleyemedi: {durum}")
        time.sleep(10)
    return vid, f"https://www.facebook.com/reel/{vid}"


if __name__ == "__main__":
    mp4 = Path(sys.argv[1])
    vid, link = yukle(mp4, json.loads(mp4.with_suffix(".json").read_text(encoding="utf-8")))
    print(f"Facebook'ta paylaşıldı: {link}")
