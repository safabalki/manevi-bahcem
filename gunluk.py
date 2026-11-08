"""Sıradaki ayetin videosunu üretip YouTube'a (varsa TikTok Instagram ve Facebook'a da) yükler ve yayinlananlar.json'a işler.

GitHub Actions her gece bunu çalıştırır; elle de çalışabilir.

Kullanım:
  python gunluk.py                   # ayetler.json'da henüz yüklenmemiş ilk ayet
  python gunluk.py --adet 3          # sıradaki 3 ayet
  python gunluk.py --id fatiha       # belirli bir ayet (daha önce yüklenmiş olsa bile)
  python gunluk.py --sadece-uret     # yükleme yok, yalnızca out/ klasörüne üret
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import facebook
import instagram
import shorts
import tiktok

KOK = Path(__file__).resolve().parent
YAYINLANANLAR = KOK / "yayinlananlar.json"
# Alafasy tilavetinde Content ID hak talebi var (Alfan Music / I-Media); YouTube hak talepli 1 dakikadan uzun
# Shorts'u dünya genelinde engelliyor (Haşr 22-24, 62 sn). Bu sınırı aşan video yüklenmez, atlanır.
EN_UZUN_SN = 58
TIKTOK_GIZLILIK = {"public": "PUBLIC_TO_EVERYONE", "unlisted": "MUTUAL_FOLLOW_FRIENDS", "private": "SELF_ONLY"}


def oku(yol, varsayilan):
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else varsayilan


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--adet", type=int, default=1)
    p.add_argument("--id")
    p.add_argument("--gizlilik", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--sadece-uret", action="store_true")
    a = p.parse_args()

    liste = oku(KOK / "ayetler.json", [])
    yayinlanan = oku(YAYINLANANLAR, [])
    if a.id:
        secilenler = [k for k in liste if k["id"] == a.id]
        if not secilenler:
            raise SystemExit(f"ayetler.json'da yok: {a.id}")
    else:
        bitenler = {y["id"] for y in yayinlanan}
        secilenler = [k for k in liste if k["id"] not in bitenler]
        if not secilenler:
            raise SystemExit("Yayınlanmamış ayet kalmadı; ayetler.json'a onaylı yeni ayet ekleyin.")

    yt = None
    if not a.sadece_uret:
        import yukle
        yt = yukle.youtube()
        print("Bağlı kanal: {1} {2} ({0})".format(*yukle.kanal_bilgisi(yt)))
    tiktok_acik = not a.sadece_uret and tiktok.TOKEN_DOSYASI.exists() and os.environ.get("TIKTOK_CLIENT_SECRET")
    # Instagram'da gizli/liste dışı paylaşım yok; yalnızca herkese açık YouTube yüklemelerinde paylaşılır.
    instagram_acik = (not a.sadece_uret and a.gizlilik == "public" and instagram.TOKEN_DOSYASI.exists()
                      and os.environ.get("INSTAGRAM_APP_SECRET"))
    facebook_acik = instagram_acik and facebook.acik()

    yuklenen = 0
    for kayit in secilenler:
        if yuklenen >= a.adet:
            break
        mp4, bilgi = shorts.video_uret(kayit)
        print(f"Üretildi: {mp4} ({bilgi['sure_sn']} sn)")
        if bilgi["sure_sn"] > EN_UZUN_SN:
            print(f"Atlandı: {kayit['id']} {bilgi['sure_sn']} sn > {EN_UZUN_SN} sn (telif engeli riski)")
            if yt is not None:
                yayinlanan.append({"id": kayit["id"], "atlandi": f"{bilgi['sure_sn']} sn, 1 dakika sınırı",
                                   "tarih": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                YAYINLANANLAR.write_text(json.dumps(yayinlanan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            continue
        yuklenen += 1
        if yt is None:
            continue
        vid = yukle.yukle(yt, mp4, bilgi, a.gizlilik)
        print(f"Yüklendi: https://youtube.com/shorts/{vid}")
        yeni = {"id": kayit["id"], "video": vid, "baslik": bilgi["baslik"], "gizlilik": a.gizlilik,
                "tarih": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if tiktok_acik:
            # TikTok hatası YouTube akışını durdurmasın; iz yayinlananlar.json'da kalır.
            try:
                pid, giz = tiktok.yukle(mp4, bilgi, TIKTOK_GIZLILIK[a.gizlilik])
                yeni["tiktok"] = {"publish_id": pid, "gizlilik": giz}
                print(f"TikTok'a gönderildi ({giz})")
            except Exception as hata:
                yeni["tiktok"] = {"hata": str(hata)[:300]}
                print(f"TikTok hatası: {hata}")
        if instagram_acik:
            try:
                mid, link = instagram.yukle(mp4, bilgi)
                yeni["instagram"] = {"id": mid, "link": link}
                print(f"Instagram'da paylaşıldı: {link or mid}")
            except Exception as hata:
                yeni["instagram"] = {"hata": str(hata)[:300]}
                print(f"Instagram hatası: {hata}")
        if facebook_acik:
            try:
                fid, link = facebook.yukle(mp4, bilgi)
                yeni["facebook"] = {"id": fid, "link": link}
                print(f"Facebook'ta paylaşıldı: {link}")
            except Exception as hata:
                yeni["facebook"] = {"hata": str(hata)[:300]}
                print(f"Facebook hatası: {hata}")
        # Her yüklemeden hemen sonra yaz: sonraki ayette hata çıksa da yüklenen tekrar yüklenmesin.
        yayinlanan.append(yeni)
        YAYINLANANLAR.write_text(json.dumps(yayinlanan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
