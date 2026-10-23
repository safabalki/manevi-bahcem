"""Onay sayfası (reviewbot) için ayet ve arka plan adaylarını hazırlar → review.json + img/.

Kullanım (review/ klasöründen):  ..\\.venv\\Scripts\\python.exe hazirla.py
"""
import html
import json
import subprocess
import sys
from pathlib import Path

import requests

BURA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURA.parent))
import pixabay  # noqa: E402
from shorts import (BAS_BOSLUK, FFMPEG, SON_BOSLUK, SURELER, ayet_getir,  # noqa: E402
                    ses_getir, sure_uzunlugu)

E = html.escape
IMG = BURA / "img"
KLIP_BASINA = 5
# Sayfaya konmadan elenenler (insan figürü, fabrika, şehir, çizim, soyut, simsiyah kareler).
ELENEN = {199788, 84634, 371741, 284566, 144597, 134252, 49377, 189230, 121128, 278610, 151053, 130071}

# Sorgu → bu kliplerin uyduğu ayet temaları
SORGULAR = {
    "sunrise clouds": ["umut", "tevekkül"],
    "sunrise mountains": ["umut", "ahlak"],
    "calm lake reflection": ["huzur", "zikir"],
    "ocean waves sunset": ["huzur", "şükür"],
    "foggy forest": ["sabır", "tefekkür"],
    "desert dunes": ["sabır", "tevekkül"],
    "night sky stars": ["dua", "tefekkür", "koruma"],
    "clouds timelapse": ["iman", "tefekkür"],
    "rain drops leaves": ["tövbe", "dua"],
    "waterfall": ["şükür", "tövbe"],
    "autumn leaves": ["ahiret"],
    "flowers blooming": ["şükür", "aile"],
    "sun rays forest": ["umut", "iman", "koruma"],
    "mosque": ["ibadet", "dua", "zikir"],
    "green meadow": ["aile", "ahlak", "huzur"],
}


def ayetleri_hazirla():
    adaylar = json.loads((BURA / "ayet-adaylari.json").read_text(encoding="utf-8"))
    for a in adaylar:
        mealler, sure = [], BAS_BOSLUK + SON_BOSLUK
        for no in range(a["bas"], a["son"] + 1):
            kelimeler, meal = ayet_getir(a["sure"], no)
            ses, _ = ses_getir(a["sure"], no, len(kelimeler))
            sure += sure_uzunlugu(ses)
            mealler.append((no, meal))
        a["mealler"], a["sure_sn"] = mealler, round(sure, 1)
        print(f"{a['id']:18} {a['sure_sn']:5} sn", flush=True)
    return adaylar


def klipleri_hazirla():
    IMG.mkdir(exist_ok=True)
    secilen, gorulen = [], set()
    for sorgu, temalar in SORGULAR.items():
        n = 0
        for k in pixabay.ara(sorgu, 60):
            if k["id"] in gorulen:
                continue
            gorulen.add(k["id"])
            if k["id"] in ELENEN:
                n += 1   # yerine yenisini çekme: elenenler zaten bakılmış adaylardı
                if n == KLIP_BASINA:
                    break
                continue
            kucuk = IMG / f"k{k['id']}.src.jpg"
            if not kucuk.exists():
                kucuk.write_bytes(requests.get(k["kucuk_resim"], timeout=60).content)
            # Videoda görünecek kısım: ortadan 9:16 kırpma (shorts.py ile aynı).
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(kucuk), "-vf",
                            "crop=ih*9/16:ih,scale=360:640", "-q:v", "4", str(IMG / f"k{k['id']}-dikey.jpg")], check=True)
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(kucuk), "-vf",
                            "scale=640:-2", "-q:v", "5", str(IMG / f"k{k['id']}-tam.jpg")], check=True)
            kucuk.unlink()
            secilen.append({**k, "temalar": temalar})
            n += 1
            if n == KLIP_BASINA:
                break
        print(f"{sorgu:22} {n} klip", flush=True)
    (BURA / "klip-adaylari.json").write_text(json.dumps(secilen, ensure_ascii=False, indent=2), encoding="utf-8")
    return secilen


def ayet_karti(a):
    sure_adi = SURELER[a["sure"] - 1]
    aralik = str(a["bas"]) if a["bas"] == a["son"] else f"{a['bas']}-{a['son']}"
    uzun = a["sure_sn"] > 59
    meal = "".join(f"<p style='margin:.35em 0'><b>{no}.</b> {E(m)}</p>" for no, m in a["mealler"])
    govde = (
        f"<p style='margin:.2em 0'><b>Başlık:</b> {E(a['baslik'])}</p>"
        f"<p style='margin:.2em 0'><b>Kanca (ilk 3 sn):</b> {E(a['kanca'])}</p>"
        f"<p style='margin:.2em 0;color:var(--ink2);font-size:14px'>Tema: {E(a['tema'])} · Süre: "
        f"{'<b style=color:#b45309>' if uzun else ''}{a['sure_sn']} sn{' (Shorts için uzun)</b>' if uzun else ''}</p>"
        f"<div style='margin-top:.6em;padding:.6em .8em;border-left:3px solid #c99a45;background:rgba(201,154,69,.08)'>"
        f"<p style='margin:0 0 .2em;font-size:13px;color:var(--ink2)'>Meal (Elmalılı), kaynaktan aynen:</p>{meal}</div>"
    )
    return {"id": f"a-{a['id']}", "title": f"{sure_adi} {aralik}", "html": govde,
            "ask": "Bu ayet, başlığı ve kancasıyla listeye girsin mi?"}


def klip_karti(i, k):
    return {
        "id": f"k-{k['id']}",
        "title": f"Klip {i}: {k['sorgu']}",
        "html": f"<p style='margin:.2em 0;color:var(--ink2);font-size:14px'>Uyduğu temalar: {E(', '.join(k['temalar']))} · "
                f"{k['sure']} sn · {k['boyut']}<br>Etiketler: {E(k['etiketler'])}</p>",
        "links": [["Pixabay'de videoyu izle", k["sayfa"]]],
        "shots": [[f"k{k['id']}-dikey.jpg", "Videoda görünecek kısım (dikey)"],
                  [f"k{k['id']}-tam.jpg", "Orijinal görüntü"]],
        "ask": "Bu görüntü kanalda kullanılabilir mi? (insan, uygunsuz detay yok)",
    }


if __name__ == "__main__":
    ayetler = ayetleri_hazirla()
    klipler = klipleri_hazirla()
    uzunlar = sum(a["sure_sn"] > 59 for a in ayetler)
    review = {
        "code": "MB-R1",
        "eyebrow": "Manevi Bahçem · 1. tur",
        "title": "Ayet listesi ve arka plan videoları",
        "lede": ("Her kartta üç düğme var: Approve = Onayla, Change = Değiştir (altına ne değişsin yazın), "
                 "Hold = Şimdilik beklet. Cevaplar dokundukça kaydedilir; yarıda bırakıp başka cihazdan devam "
                 "edebilirsiniz. Bitince en üstteki \"I'm done, go\" düğmesine basın ve bana sohbette \"bitti\" yazın."),
        "status": [[f"Ayet: {len(ayetler)}", "wait"], [f"Klip: {len(klipler)}", "wait"],
                   [f"60 sn'den uzun ayet: {uzunlar}", "wait" if uzunlar else "ok"]],
        "sections": [
            {"id": "ayetler", "eyebrow": "Günün Ayeti serisi", "title": "Seçme ayetler",
             "intro": ("Her gece bu listeden sıradaki ayet yayınlanacak. Başlık videonun YouTube başlığı, kanca ilk 3 saniyede "
                       "ekranda çıkan cümle. Meal kaynaktan aynen geliyor; başlık ve kancanın meale uygun olup olmadığına bakın."),
             "cards": [ayet_karti(a) for a in ayetler]},
            {"id": "klipler", "eyebrow": "Arka plan kütüphanesi", "title": "Arka plan videoları",
             "intro": ("Sadece onayladığınız klipler kullanılacak. Soldaki resim videoda görünecek dikey kısım, sağdaki orijinal "
                       "görüntü. Videonun tamamında insan ya da uygunsuz bir şey var mı diye emin olmak için Pixabay "
                       "bağlantısından izleyebilirsiniz."),
             "cards": [klip_karti(i, k) for i, k in enumerate(klipler, 1)]},
        ],
        "answered": [
            {"text": "Kanal adı ve adresi", "answer": "Manevi Bahçem, @manevibahcem"},
            {"text": "Türkçe seslendirme olsun mu?", "answer": "Hayır, sadece Arapça tilavet"},
            {"text": "Kanca yazısı", "answer": "Sadece ilk 3 saniye görünsün"},
            {"text": "Meal", "answer": "Elmalılı Hamdi Yazır (telif serbest)"},
        ],
        "general_prompt": "Listeye eklemek istediğiniz ayetler, genel görüşler, yeni fikirler",
    }
    (BURA / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"review.json: {len(ayetler)} ayet, {len(klipler)} klip, {uzunlar} uzun")
