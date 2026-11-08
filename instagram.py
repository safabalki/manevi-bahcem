"""Instagram'a Reels yükler (Instagram Graph API, Facebook Login yolu: dosya doğrudan Meta'ya yüklenir).

Neden Facebook Login: "Instagram Login" yolu videoyu yalnızca herkese açık bir adresten (video_url) alıyor; bizim
videolarımız gizli depoda. Facebook Login yolu dosyanın kendisini rupload.facebook.com'a yüklemeye izin veriyor.
Gereken: Instagram hesabı profesyonel (İçerik üretici/İşletme) olmalı ve bir Facebook Sayfasına bağlı olmalı.

Token: Graph API Explorer'dan alınan kısa ömürlü kullanıcı token'ı --bagla ile uzun ömürlüye çevrilir; ondan
türetilen Sayfa token'ı süresizdir. Depoda şifreli durur (instagram-token.enc; anahtar = SHA256(INSTAGRAM_APP_SECRET)).

Kullanım:
  python instagram.py --bagla KISA_TOKEN --kullanici manevibahcem   # yalnızca bu Instagram hesabına bağlanır
  python instagram.py --sil DffaEapjH0r    # paylaşımı sil (Reels bağlantısındaki kod ya da medya id)
  python instagram.py --bilgi              # bağlı hesap ve 24 saatlik yayın kotası
  python instagram.py out/x.mp4            # yanındaki .json'daki açıklamayla Reels olarak paylaş
"""
import argparse
import base64
import hashlib
import json
import os
import time
from pathlib import Path

import requests
from cryptography.fernet import Fernet, InvalidToken

KOK = Path(__file__).resolve().parent
TOKEN_DOSYASI = KOK / "instagram-token.enc"
SURUM = "v24.0"
GRAPH = f"https://graph.facebook.com/{SURUM}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{SURUM}"


def _sifre():
    anahtar = hashlib.sha256(os.environ["INSTAGRAM_APP_SECRET"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(anahtar))


def _cevap(r, ne):
    try:
        veri = r.json()
    except ValueError:
        veri = {"error": {"message": r.text[:300]}}
    if "error" in veri:
        h = veri["error"]
        raise RuntimeError(f"Instagram {ne}: {h.get('message')} (kod {h.get('code')}/{h.get('error_subcode')})")
    return veri


def _get(yol, **params):
    return _cevap(requests.get(f"{GRAPH}{yol}", params=params, timeout=60), yol)


def bagla(kisa_token, kullanici):
    uzun = _get("/oauth/access_token", grant_type="fb_exchange_token", client_id=os.environ["INSTAGRAM_APP_ID"],
                client_secret=os.environ["INSTAGRAM_APP_SECRET"], fb_exchange_token=kisa_token)["access_token"]
    sayfalar = _get("/me/accounts", access_token=uzun,
                    fields="id,name,access_token,instagram_business_account{id,username}")["data"]
    # Kullanıcı birden çok Sayfa yönetebiliyor (2026-11-08: ilk Sayfa başka bir işletmenindi ve deneme oraya gitti).
    # Bu yüzden hesap adı zorunlu ve birebir eşleşmeli; asla "ilk bulunan" seçilmez.
    kullanici = kullanici.strip().lstrip("@").lower()
    bagli = [s for s in sayfalar if s.get("instagram_business_account")]
    uyan = [s for s in bagli if s["instagram_business_account"].get("username", "").lower() == kullanici]
    if len(uyan) != 1:
        bulunan = ", ".join(f"{s['name']} → @{s['instagram_business_account'].get('username')}" for s in bagli)
        diger = ", ".join(s["name"] for s in sayfalar if not s.get("instagram_business_account"))
        raise RuntimeError(f"@{kullanici} bağlı tek bir Facebook Sayfası bulunamadı. Instagram bağlı Sayfalar: "
                           f"{bulunan or 'yok'}; Instagram'sız Sayfalar: {diger or 'yok'}. Instagram'ı profesyonel "
                           "hesaba çevirip doğru Sayfaya bağlayın; token alırken yalnızca o Sayfayı seçin.")
    s = uyan[0]
    ig = s["instagram_business_account"]
    t = {"sayfa_id": s["id"], "sayfa": s["name"], "ig_id": ig["id"], "kullanici": ig.get("username"),
         "token": s["access_token"], "alindi": int(time.time())}
    TOKEN_DOSYASI.write_bytes(_sifre().encrypt(json.dumps(t).encode()))
    print(f"Bağlandı: @{t['kullanici']} (Sayfa: {t['sayfa']})")


def erisim():
    if not TOKEN_DOSYASI.exists():
        raise RuntimeError("Instagram bağlı değil (instagram-token.enc yok); önce 'Instagram Bağla' çalıştırılmalı.")
    try:
        return json.loads(_sifre().decrypt(TOKEN_DOSYASI.read_bytes()))
    except InvalidToken:
        raise RuntimeError("instagram-token.enc çözülemedi (INSTAGRAM_APP_SECRET değişmiş); yeniden bağlayın.")


def aciklama(bilgi):
    metin = bilgi["aciklama"].replace("#shorts ", "").replace("abone olun", "takip edin")
    return f"{bilgi['baslik']}\n\n{metin} #reels #islam"[:2200]


def yukle(mp4, bilgi):
    """Reels olarak paylaşır. Dönüş: (medya id, kalıcı bağlantı)."""
    t = erisim()
    yetki = {"Authorization": f"OAuth {t['token']}"}
    kap = _cevap(requests.post(f"{GRAPH}/{t['ig_id']}/media", headers=yetki, timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": aciklama(bilgi),
        "share_to_feed": "true", "thumb_offset": "3500"}), "kapsayıcı")["id"]
    boyut = mp4.stat().st_size
    with open(mp4, "rb") as f:
        _cevap(requests.post(f"{RUPLOAD}/{kap}", data=f, timeout=600, headers={
            **yetki, "offset": "0", "file_size": str(boyut), "Content-Type": "application/octet-stream"}), "yükleme")
    # Meta videoyu işler; FINISHED olmadan yayınlanamaz.
    for _ in range(60):
        durum = _cevap(requests.get(f"{GRAPH}/{kap}", headers=yetki, timeout=60,
                                    params={"fields": "status_code,status"}), "durum")
        if durum.get("status_code") == "FINISHED":
            break
        if durum.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram videoyu işleyemedi: {durum.get('status')}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram videoyu 10 dakikada işlemedi")
    mid = _cevap(requests.post(f"{GRAPH}/{t['ig_id']}/media_publish", headers=yetki, timeout=60,
                               data={"creation_id": kap}), "yayın")["id"]
    try:
        link = _get(f"/{mid}", access_token=t["token"], fields="permalink").get("permalink")
    except RuntimeError:
        link = None
    return mid, link


def sil(kod):
    """Paylaşımı siler. kod: Reels bağlantısındaki kısa kod (instagram.com/reel/KOD) ya da medya id."""
    t = erisim()
    mid = kod
    if not kod.isdigit():
        sonraki = f"{GRAPH}/{t['ig_id']}/media"
        params = {"access_token": t["token"], "fields": "id,permalink", "limit": 50}
        mid = None
        while sonraki and mid is None:
            veri = _cevap(requests.get(sonraki, params=params, timeout=60), "medya listesi")
            mid = next((m["id"] for m in veri["data"] if f"/{kod}/" in m.get("permalink", "")), None)
            sonraki, params = veri.get("paging", {}).get("next"), None
        if mid is None:
            raise RuntimeError(f"@{t['kullanici']} hesabında {kod} bulunamadı")
    _cevap(requests.delete(f"{GRAPH}/{mid}", params={"access_token": t["token"]}, timeout=60), "silme")
    print(f"Silindi: {kod} (@{t['kullanici']})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video", nargs="?")
    p.add_argument("--bagla")
    p.add_argument("--kullanici", help="bağlanacak Instagram hesabı (zorunlu, ör. manevibahcem)")
    p.add_argument("--bilgi", action="store_true")
    p.add_argument("--sil")
    a = p.parse_args()
    if a.bagla:
        if not a.kullanici:
            p.error("--bagla için --kullanici zorunlu")
        bagla(a.bagla.strip(), a.kullanici)
    if a.sil:
        sil(a.sil.strip())
    if a.bilgi or a.bagla:
        t = erisim()
        kota = _get(f"/{t['ig_id']}/content_publishing_limit", access_token=t["token"],
                    fields="quota_usage,config")["data"]
        print(f"Hesap: @{t['kullanici']} · Sayfa: {t['sayfa']} · 24 saatlik kota: {kota}")
    if a.video:
        mp4 = Path(a.video)
        mid, link = yukle(mp4, json.loads(mp4.with_suffix(".json").read_text(encoding="utf-8")))
        print(f"Instagram'da paylaşıldı: {link or mid}")
