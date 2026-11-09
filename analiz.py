"""YouTube izlenme analizi: yayinlananlar.json'daki videoların istatistikleri, tema ve saat ortalamaları.

YouTube Data API (youtube.readonly, yükleme token'ıyla aynı) kullanılır; kota maliyeti 50 video başına 1 birim.
Silinmiş/erişilemeyen videolar "YOK" olarak işaretlenir (instagram_gecmis.py bunları atlar).

Kullanım:
  python analiz.py              # tabloyu yazdırır; Actions'ta özet sekmesine de yazar
  python analiz.py --json x.json
"""
import argparse
import json
import os
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent
TR = timezone(timedelta(hours=3))


def istatistikler(yt, kimlikler):
    """{video_id: {...}}; listede olmayan video silinmiş ya da erişilemez demektir."""
    sonuc = {}
    for i in range(0, len(kimlikler), 50):
        cevap = yt.videos().list(part="statistics,status,contentDetails",
                                 id=",".join(kimlikler[i:i + 50])).execute()
        for v in cevap.get("items", []):
            s = v.get("statistics", {})
            sonuc[v["id"]] = {
                "izlenme": int(s.get("viewCount", 0)), "begeni": int(s.get("likeCount", 0)),
                "yorum": int(s.get("commentCount", 0)), "gizlilik": v["status"].get("privacyStatus"),
                "engel": bool(v.get("contentDetails", {}).get("regionRestriction", {}).get("blocked")),
            }
    return sonuc


def rapor(yt):
    ayetler = {a["id"]: a for a in json.loads((KOK / "ayetler.json").read_text(encoding="utf-8"))}
    yayinlanan = [y for y in json.loads((KOK / "yayinlananlar.json").read_text(encoding="utf-8")) if "video" in y]
    ist = istatistikler(yt, [y["video"] for y in yayinlanan])
    simdi = datetime.now(timezone.utc)
    satirlar = []
    for y in yayinlanan:
        tarih = datetime.fromisoformat(y["tarih"])
        s = ist.get(y["video"])
        gun = max((simdi - tarih).total_seconds() / 86400, 0.5)
        satirlar.append({
            "id": y["id"], "video": y["video"], "baslik": y["baslik"], "tema": ayetler.get(y["id"], {}).get("tema", "?"),
            "saat": (lambda h: "sabah (07)" if h < 12 else "öğle (13)" if h < 17 else "akşam (19)")(tarih.astimezone(TR).hour), "gun": round(gun, 1), "yok": s is None,
            **(s or {"izlenme": 0, "begeni": 0, "yorum": 0, "gizlilik": None, "engel": False}),
            "gunluk": round((s or {}).get("izlenme", 0) / gun, 1),
        })
    return satirlar


def kanal(yt):
    s = yt.channels().list(part="statistics", mine=True).execute()["items"][0]["statistics"]
    return {"abone": int(s.get("subscriberCount", 0)), "izlenme": int(s.get("viewCount", 0)),
            "video": int(s.get("videoCount", 0))}


def instagram_durum():
    """Takipçi ve son Reels beğeni/yorum sayıları (izlenme için ayrı izin gerekiyor, yok)."""
    import instagram
    t = instagram.erisim()
    hesap = instagram._get(f"/{t['ig_id']}", access_token=t["token"], fields="followers_count,media_count")
    medya = instagram._get(f"/{t['ig_id']}/media", access_token=t["token"], limit=50,
                           fields="caption,like_count,comments_count,permalink")["data"]
    return {"takipci": hesap.get("followers_count", 0), "gonderi": hesap.get("media_count", 0),
            "begeni": sum(m.get("like_count", 0) for m in medya),
            "yorum": sum(m.get("comments_count", 0) for m in medya),
            "enler": sorted(medya, key=lambda m: -m.get("like_count", 0))[:5]}


def hesaplar_metni(k, ig):
    cizgi = ["## Hesaplar\n"]
    if k:
        cizgi.append(f"- **YouTube:** {k['abone']:,} abone · {k['izlenme']:,} toplam izlenme · {k['video']} video")
    if isinstance(ig, dict):
        cizgi.append(f"- **Instagram:** {ig['takipci']:,} takipçi · {ig['gonderi']} gönderi · "
                     f"son gönderilerde {ig['begeni']:,} beğeni, {ig['yorum']} yorum")
        for m in ig["enler"]:
            ad = (m.get("caption") or "").split("\n")[0][:60]
            cizgi.append(f"  - {m.get('like_count', 0)} beğeni · [{ad}]({m.get('permalink')})")
    elif ig:
        cizgi.append(f"- **Instagram:** okunamadı ({ig})")
    return "\n".join(cizgi) + "\n\n"


def ozet(satirlar):
    canli = [s for s in satirlar if not s["yok"]]
    cizgi = []
    toplam = sum(s["izlenme"] for s in canli)
    cizgi.append(f"## Özet\n\n{len(canli)} video, toplam **{toplam:,}** izlenme, "
                 f"{sum(s['begeni'] for s in canli):,} beğeni, {sum(s['yorum'] for s in canli):,} yorum. "
                 f"Medyan izlenme: {statistics.median([s['izlenme'] for s in canli]) if canli else 0:,.0f}.\n")
    yok = [s for s in satirlar if s["yok"]]
    if yok:
        cizgi.append("Silinmiş/erişilemeyen: " + ", ".join(f"{s['id']} ({s['video']})" for s in yok) + "\n")
    engelli = [s for s in canli if s["engel"]]
    if engelli:
        cizgi.append("Bölge engelli: " + ", ".join(s["id"] for s in engelli) + "\n")

    for baslik, anahtar in (("Tema", "tema"), ("Dilim (TR, fiilen yüklendiği saat)", "saat")):
        grup = defaultdict(list)
        for s in canli:
            grup[s[anahtar]].append(s)
        cizgi.append(f"\n## {baslik}\n\n| {baslik.split()[0]} | Video | Ort. izlenme | Medyan | Ort. günlük |\n|---|---|---|---|---|")
        for k, g in sorted(grup.items(), key=lambda kv: -statistics.mean(x["izlenme"] for x in kv[1])):
            cizgi.append(f"| {k} | {len(g)} | {statistics.mean(x['izlenme'] for x in g):,.0f} | "
                         f"{statistics.median(x['izlenme'] for x in g):,.0f} | "
                         f"{statistics.mean(x['gunluk'] for x in g):,.1f} |")

    cizgi.append("\n## Videolar (izlenmeye göre)\n\n| # | Ayet | Tema | İzlenme | Beğeni | Yorum | Gün | Günlük |\n"
                 "|---|---|---|---|---|---|---|---|")
    for i, s in enumerate(sorted(canli, key=lambda x: -x["izlenme"]), 1):
        cizgi.append(f"| {i} | [{s['baslik']}](https://youtube.com/shorts/{s['video']}) | {s['tema']} | "
                     f"{s['izlenme']:,} | {s['begeni']} | {s['yorum']} | {s['gun']} | {s['gunluk']} |")
    return "\n".join(cizgi) + "\n"


if __name__ == "__main__":
    import yukle
    p = argparse.ArgumentParser()
    p.add_argument("--json")
    p.add_argument("--kaydet", action="store_true", help="rapor/analiz.md ve rapor/<tarih>.md olarak yaz")
    a = p.parse_args()
    yt = yukle.youtube()
    satirlar = rapor(yt)
    ig = None
    if os.environ.get("INSTAGRAM_APP_SECRET"):
        try:
            ig = instagram_durum()
        except Exception as hata:
            ig = str(hata)[:200]
    metin = hesaplar_metni(kanal(yt), ig) + ozet(satirlar)
    print(metin)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(metin)
    if a.kaydet:
        klasor = KOK / "rapor"
        klasor.mkdir(exist_ok=True)
        tarih = datetime.now(TR).strftime("%Y-%m-%d")
        metin = f"# Analiz {tarih}\n\n" + metin
        (klasor / "analiz.md").write_text(metin, encoding="utf-8")
        (klasor / f"{tarih}.md").write_text(metin, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(satirlar, ensure_ascii=False, indent=2), encoding="utf-8")
