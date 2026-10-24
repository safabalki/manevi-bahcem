"""Sıradaki ayetin videosunu üretip YouTube'a yükler ve yayinlananlar.json'a işler.

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

import shorts
import tiktok

KOK = Path(__file__).resolve().parent
YAYINLANANLAR = KOK / "yayinlananlar.json"
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
        secilenler = [k for k in liste if k["id"] not in bitenler][:a.adet]
        if not secilenler:
            raise SystemExit("Yayınlanmamış ayet kalmadı; ayetler.json'a onaylı yeni ayet ekleyin.")

    yt = None
    if not a.sadece_uret:
        import yukle
        yt = yukle.youtube()
        print("Bağlı kanal: {1} {2} ({0})".format(*yukle.kanal_bilgisi(yt)))
    tiktok_acik = not a.sadece_uret and tiktok.TOKEN_DOSYASI.exists() and os.environ.get("TIKTOK_CLIENT_SECRET")

    for kayit in secilenler:
        mp4, bilgi = shorts.video_uret(kayit)
        print(f"Üretildi: {mp4} ({bilgi['sure_sn']} sn)")
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
        # Her yüklemeden hemen sonra yaz: sonraki ayette hata çıksa da yüklenen tekrar yüklenmesin.
        yayinlanan.append(yeni)
        YAYINLANANLAR.write_text(json.dumps(yayinlanan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
