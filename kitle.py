"""Kitle dağılımı: YouTube (yaş, cinsiyet, ülke, şehir) ve Instagram (takipçi yaş/cinsiyet/şehir).

YouTube Analytics API `yt-analytics.readonly` izni ister. Yükleme token'ı bu izni içermiyorsa yükleme bozulmasın
diye ayrı bir kimlikle (scope belirtmeden) denenir; izin yoksa {"hata": ...} döner.
Instagram `follower_demographics` için `instagram_manage_insights` izni ve en az 100 takipçi gerekir.
Facebook Sayfası demografisi (page_fans_city vb.) Meta tarafından 2024'te kaldırıldı → yok.

Kullanım: python kitle.py   (JSON yazdırır)
"""
import json
import os
from datetime import datetime

from analiz import TR

YAS = {"age13-17": "13-17", "age18-24": "18-24", "age25-34": "25-34", "age35-44": "35-44",
       "age45-54": "45-54", "age55-64": "55-64", "age65-": "65+"}
CINSIYET = {"male": "Erkek", "female": "Kadın", "user_specified": "Belirtilmemiş"}
BASLANGIC = "2026-10-01"


def _analytics():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import yukle
    if os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        bilgi = {"refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
                 "client_id": os.environ["YOUTUBE_CLIENT_ID"], "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"]}
    elif os.environ.get("YOUTUBE_TOKEN"):
        bilgi = json.loads(os.environ["YOUTUBE_TOKEN"])
    else:
        bilgi = json.loads((yukle.KOK / "token.json").read_text(encoding="utf-8"))
    kimlik = Credentials(None, refresh_token=bilgi["refresh_token"], token_uri="https://oauth2.googleapis.com/token",
                         client_id=bilgi["client_id"], client_secret=bilgi["client_secret"])
    kimlik.refresh(Request())
    return build("youtubeAnalytics", "v2", credentials=kimlik, cache_discovery=False)


def youtube():
    try:
        ya = _analytics()
        bugun = datetime.now(TR).date().isoformat()
        sor = lambda **k: ya.reports().query(ids="channel==MINE", startDate=BASLANGIC, endDate=bugun, **k).execute()
        yc = sor(metrics="viewerPercentage", dimensions="ageGroup,gender").get("rows") or []
        yas, cins = {}, {}
        for g, c, y in yc:
            yas[YAS.get(g, g)] = yas.get(YAS.get(g, g), 0) + y
            cins[CINSIYET.get(c, c)] = cins.get(CINSIYET.get(c, c), 0) + y
        ulke = sor(metrics="views,subscribersGained", dimensions="country", sort="-views", maxResults=10).get("rows") or []
        sehir = []
        try:
            sehir = sor(metrics="views", dimensions="city", sort="-views", maxResults=10).get("rows") or []
        except Exception as hata:
            print("Şehir raporu alınamadı:", str(hata)[:150])
        return {"yas": [{"ad": k, "yuzde": round(v, 1)} for k, v in sorted(yas.items())],
                "cinsiyet": [{"ad": k, "yuzde": round(v, 1)} for k, v in sorted(cins.items(), key=lambda x: -x[1])],
                "ulke": [{"kod": r[0], "izlenme": r[1], "abone": r[2]} for r in ulke],
                "sehir": [{"ad": r[0], "izlenme": r[1]} for r in sehir]}
    except Exception as hata:
        return {"hata": str(hata)[:200]}


def instagram():
    try:
        import instagram as ig
        t = ig.erisim()
        sonuc = {}
        for kirilim in ("age", "gender", "city"):
            veri = ig._get(f"/{t['ig_id']}/insights", access_token=t["token"], metric="follower_demographics",
                           period="lifetime", metric_type="total_value", breakdown=kirilim)["data"]
            satirlar = veri[0]["total_value"]["breakdowns"][0]["results"] if veri else []
            sonuc[kirilim] = sorted(({"ad": r["dimension_values"][0], "sayi": r["value"]} for r in satirlar),
                                    key=lambda r: -r["sayi"])[:10]
        if "gender" in sonuc:
            harf = {"M": "Erkek", "F": "Kadın", "U": "Belirtilmemiş"}
            for r in sonuc["gender"]:
                r["ad"] = harf.get(r["ad"], r["ad"])
        return sonuc
    except Exception as hata:
        return {"hata": str(hata)[:200]}


def topla():
    k = {"youtube": youtube()}
    if os.environ.get("INSTAGRAM_APP_SECRET"):
        k["instagram"] = instagram()
    return k


def metin(k):
    """analiz.py raporu için Markdown."""
    s = ["## Kitle\n"]
    y = k.get("youtube", {})
    if "hata" in y:
        s.append(f"- **YouTube:** okunamadı — YouTube Analytics izni gerekiyor ({y['hata'][:100]})")
    else:
        s.append("- **YouTube yaş:** " + ", ".join(f"{r['ad']} %{r['yuzde']}" for r in y["yas"]))
        s.append("- **YouTube cinsiyet:** " + ", ".join(f"{r['ad']} %{r['yuzde']}" for r in y["cinsiyet"]))
        s.append("- **YouTube ülke (izlenme):** " + ", ".join(f"{r['kod']} {r['izlenme']:,}" for r in y["ulke"]))
        if y["sehir"]:
            s.append("- **YouTube şehir (izlenme):** " + ", ".join(f"{r['ad']} {r['izlenme']:,}" for r in y["sehir"]))
    i = k.get("instagram")
    if isinstance(i, dict):
        if "hata" in i:
            s.append(f"- **Instagram:** okunamadı (instagram_manage_insights izni ve 100+ takipçi gerekir; {i['hata'][:80]})")
        else:
            for ad, bas in (("age", "yaş"), ("gender", "cinsiyet"), ("city", "şehir")):
                s.append(f"- **Instagram {bas}:** " + ", ".join(f"{r['ad']} {r['sayi']}" for r in i.get(ad, [])))
    return "\n".join(s) + "\n\n"


if __name__ == "__main__":
    print(json.dumps(topla(), ensure_ascii=False, indent=2))
