"""TikTok'a video yükler (Content Posting API: Direct Post, olmazsa gelen kutusuna taslak).

Token depoda şifreli durur (tiktok-token.enc); anahtarı TIKTOK_CLIENT_SECRET'tan türetilir. TikTok her yenilemede
yeni refresh token verebildiği için dosya her kullanımda güncellenir ve Actions depoya geri yazar.

Kullanım:
  python tiktok.py --bagla KOD           # tiktok.html'in gösterdiği izin koduyla hesabı bağla
  python tiktok.py --bilgi               # bağlı hesabı ve izinli gizlilik seçeneklerini göster
  python tiktok.py out/x.mp4             # yanındaki .json'daki başlıkla yükle
"""
import argparse
import base64
import hashlib
import json
import math
import os
import time
from pathlib import Path

import requests
from cryptography.fernet import Fernet

KOK = Path(__file__).resolve().parent
TOKEN_DOSYASI = KOK / "tiktok-token.enc"
API = "https://open.tiktokapis.com/v2"
YONLENDIRME = "https://safabalki.github.io/tiktok.html"
PARCA = 10 << 20   # TikTok: parça 5–64 MB, son parça kalanı da alır


def _sifre():
    anahtar = hashlib.sha256(os.environ["TIKTOK_CLIENT_SECRET"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(anahtar))


def _token_yaz(t):
    t["alindi"] = int(time.time())
    TOKEN_DOSYASI.write_bytes(_sifre().encrypt(json.dumps(t).encode()))


def _token_istegi(**alanlar):
    r = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"], **alanlar,
    })
    t = r.json()
    if "access_token" not in t:
        raise SystemExit(f"TikTok token hatası: {t.get('error')} {t.get('error_description')}")
    _token_yaz(t)
    return t


def bagla(kod):
    t = _token_istegi(code=kod, grant_type="authorization_code", redirect_uri=YONLENDIRME)
    print(f"Bağlandı. İzinler: {t.get('scope')}")


def erisim():
    if not TOKEN_DOSYASI.exists():
        raise SystemExit("TikTok bağlı değil (tiktok-token.enc yok); önce 'TikTok Bağla' çalıştırılmalı.")
    t = json.loads(_sifre().decrypt(TOKEN_DOSYASI.read_bytes()))
    if time.time() > t["alindi"] + t["expires_in"] - 600:
        t = _token_istegi(grant_type="refresh_token", refresh_token=t["refresh_token"])
    return t["access_token"]


def _post(token, yol, govde):
    r = requests.post(f"{API}{yol}", json=govde, timeout=60, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    cevap = r.json()
    if cevap.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok {yol}: {cevap['error']}")
    return cevap["data"]


def hesap(token):
    return _post(token, "/post/publish/creator_info/query/", {})


def aciklama(bilgi):
    metin = bilgi["aciklama"].replace("#shorts ", "").replace("abone olun", "takip edin")
    return f"{bilgi['baslik']}\n\n{metin} #islam #fyp"[:2200]


def _gonder(token, yol, govde, mp4):
    """init isteği + dosyanın parça parça yüklenmesi; publish_id döner."""
    boyut = mp4.stat().st_size
    parca = boyut if boyut <= PARCA else PARCA
    adet = max(1, boyut // parca)
    govde["source_info"] = {"source": "FILE_UPLOAD", "video_size": boyut, "chunk_size": parca,
                            "total_chunk_count": adet}
    veri = _post(token, yol, govde)
    with open(mp4, "rb") as f:
        for i in range(adet):
            bas = i * parca
            son = boyut - 1 if i == adet - 1 else bas + parca - 1
            f.seek(bas)
            r = requests.put(veri["upload_url"], data=f.read(son - bas + 1), timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Range": f"bytes {bas}-{son}/{boyut}"})
            r.raise_for_status()
    return veri["publish_id"]


def yukle(mp4, bilgi, gizlilik=None):
    """Videoyu gönderir; TikTok işleyene kadar bekler. Dönüş: (publish_id, gizlilik ya da "TASLAK").

    Denetlenmemiş uygulama herkese açık hesaba doğrudan paylaşamıyor; o zaman video taslak olarak
    TikTok gelen kutusuna gider, kullanıcı uygulamada "Paylaş"a basar.
    """
    token = erisim()
    secenekler = hesap(token)["privacy_level_options"]
    gizlilik = gizlilik if gizlilik in secenekler else ("SELF_ONLY" if "SELF_ONLY" in secenekler else secenekler[0])
    try:
        pid = _gonder(token, "/post/publish/video/init/", {"post_info": {
            "title": aciklama(bilgi), "privacy_level": gizlilik, "disable_duet": False,
            "disable_comment": False, "disable_stitch": False, "video_cover_timestamp_ms": 3500}}, mp4)
    except RuntimeError as hata:
        if "unaudited_client" not in str(hata):
            raise
        pid, gizlilik = _gonder(token, "/post/publish/inbox/video/init/", {}, mp4), "TASLAK"
    for _ in range(60):
        durum = _post(token, "/post/publish/status/fetch/", {"publish_id": pid})
        if durum["status"] in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            break
        if durum["status"] == "FAILED":
            raise RuntimeError(f"TikTok yükleme başarısız: {durum.get('fail_reason')}")
        time.sleep(5)
    return pid, gizlilik


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video", nargs="?")
    p.add_argument("--bagla")
    p.add_argument("--bilgi", action="store_true")
    a = p.parse_args()
    if a.bagla:
        bagla(a.bagla.strip())
    if a.bilgi or a.bagla:
        h = hesap(erisim())
        print(f"Hesap: @{h['creator_username']} · gizlilik seçenekleri: {h['privacy_level_options']}"
              f" · en uzun video: {h['max_video_post_duration_sec']} sn")
    if a.video:
        mp4 = Path(a.video)
        pid, giz = yukle(mp4, json.loads(mp4.with_suffix(".json").read_text(encoding="utf-8")))
        print(f"TikTok'a gönderildi ({giz}): {pid}")
