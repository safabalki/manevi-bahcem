"""İstatistik sitesi (manevibahcem.safabalki.com.tr) için herkese açık özet veriyi üretir ve siteye gönderir.

Yalnızca herkese açık bilgiler gider: takipçi/izlenme sayıları, video başlıkları ve bağlantıları. Gönderim GitHub
Actions'ın OIDC belgesiyle doğrulanır (web/yukle.php); paylaşılan şifre yok.

Kullanım (Actions'ta, permissions: id-token: write):
  python site_veri.py              # üret + gönder
  python site_veri.py --yalniz-uret veri.json
"""
import argparse
import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

import requests

import analiz
from analiz import KOK, TR

SITE = "https://manevibahcem.safabalki.com.tr/yukle.php"
KITLE = "manevibahcem-site"
LINKLER = {
    "youtube": "https://www.youtube.com/@manevibahcem",
    "instagram": "https://www.instagram.com/manevibahcem.tr/",
    "tiktok": "https://www.tiktok.com/@manevibahcem",
}


def uret():
    import yukle
    yt = yukle.youtube()
    k = analiz.kanal(yt)
    satirlar = [s for s in analiz.rapor(yt) if not s["yok"]]
    kayitlar = json.loads((KOK / "yayinlananlar.json").read_text(encoding="utf-8"))
    videolar = [x for x in kayitlar if "video" in x]
    simdi = datetime.now(TR)
    ilk = min(datetime.fromisoformat(x["tarih"]) for x in videolar).astimezone(TR)
    basarili = lambda p: sum(1 for x in kayitlar if p in x and "hata" not in x[p])

    p = {"youtube": {"takipci": k["abone"], "izlenme": k["izlenme"], "video": len(videolar),
                     "url": LINKLER["youtube"]},
         "tiktok": {"video": basarili("tiktok"), "url": LINKLER["tiktok"]}}
    if os.environ.get("INSTAGRAM_APP_SECRET"):
        try:
            ig = analiz.instagram_durum()
            p["instagram"] = {"takipci": ig["takipci"], "gonderi": ig["gonderi"], "begeni": ig["begeni"],
                              "video": basarili("instagram"), "url": LINKLER["instagram"]}
        except Exception as hata:
            print("Instagram okunamadı:", hata)
        try:
            import instagram
            fb = analiz.facebook_durum()
            p["facebook"] = {"takipci": fb["takipci"], "begeni": (fb.get("reels") or {}).get("begeni"),
                             "video": basarili("facebook"),
                             "url": f"https://www.facebook.com/{instagram.erisim()['sayfa_id']}"}
        except Exception as hata:
            print("Facebook okunamadı:", hata)

    temalar = defaultdict(list)
    for s in satirlar:
        temalar[s["tema"]].append(s["izlenme"])
    kart = lambda s: {"baslik": s["baslik"], "url": f"https://youtube.com/shorts/{s['video']}",
                      "izlenme": s["izlenme"], "begeni": s["begeni"], "tema": s["tema"]}
    son = sorted(videolar, key=lambda x: x["tarih"], reverse=True)[:8]
    ist = {s["video"]: s for s in satirlar}
    import kitle
    return {
        "kitle": kitle.topla(),
        "guncelleme": simdi.isoformat(timespec="minutes"),
        "baslangic": ilk.date().isoformat(),
        "gun": (simdi - ilk).days,
        "platformlar": p,
        "youtube_ozet": {"toplam_izlenme": sum(s["izlenme"] for s in satirlar),
                         "toplam_begeni": sum(s["begeni"] for s in satirlar),
                         "medyan": statistics.median(s["izlenme"] for s in satirlar) if satirlar else 0},
        "enler": [kart(s) for s in sorted(satirlar, key=lambda s: -s["izlenme"])[:10]],
        "sonlar": [dict(kart(ist[x["video"]]), tarih=x["tarih"][:10]) for x in son if x["video"] in ist],
        "temalar": sorted(({"tema": t, "ortalama": round(statistics.mean(v)), "video": len(v)}
                           for t, v in temalar.items()), key=lambda t: -t["ortalama"]),
    }


def gonder(veri):
    r = requests.get(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + f"&audience={KITLE}", timeout=30,
                     headers={"Authorization": f"bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}"})
    r.raise_for_status()
    cevap = requests.post(SITE, data=json.dumps(veri, ensure_ascii=False).encode("utf-8"), timeout=60,
                          headers={"Authorization": f"Bearer {r.json()['value']}",
                                   "Content-Type": "application/json; charset=utf-8"})
    print("Site:", cevap.status_code, cevap.text[:200])
    cevap.raise_for_status()


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--yalniz-uret")
    args = a.parse_args()
    veri = uret()
    if args.yalniz_uret:
        open(args.yalniz_uret, "w", encoding="utf-8").write(json.dumps(veri, ensure_ascii=False, indent=2))
    else:
        gonder(veri)
