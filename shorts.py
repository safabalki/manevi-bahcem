"""Seçilen ayetlerden dikey YouTube Shorts videosu üretir.

Arapça metin, tilavet ve kelime zamanlamaları api.quran.com'dan, meal
api.alquran.cloud'dan gelir; hiçbir Kur'an metni burada elle yazılmaz ya da üretilmez.

Kullanım:  python shorts.py [ayet-id]
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import requests

KOK = Path(__file__).resolve().parent
CACHE = KOK / "cache"
CIKTI = KOK / "out"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

KANAL = "MANEVİ BAHÇEM"
MEAL = ("tr.yazir", "Elmalılı Hamdi Yazır")
KARI = (7, "Mishary Raşid Alafasy")   # quran.com recitation id
FPS = 30
BAS_BOSLUK = 0.25   # ilk ayetten önceki sessizlik (sn)
SON_BOSLUK = 1.2    # son ayetten sonra yazı ekranda kalsın
GECIS = 0.35        # ayetler arası yazı geçişi (sn)
KANCA_SN = 3.0      # kanca yazısının ekranda kaldığı süre (sn)

SURELER = [
    "Fatiha", "Bakara", "Al-i İmran", "Nisa", "Maide", "En'am", "A'raf", "Enfal", "Tevbe", "Yunus",
    "Hud", "Yusuf", "Ra'd", "İbrahim", "Hicr", "Nahl", "İsra", "Kehf", "Meryem", "Taha",
    "Enbiya", "Hac", "Mü'minun", "Nur", "Furkan", "Şuara", "Neml", "Kasas", "Ankebut", "Rum",
    "Lokman", "Secde", "Ahzab", "Sebe", "Fatır", "Yasin", "Saffat", "Sad", "Zümer", "Mü'min",
    "Fussilet", "Şura", "Zuhruf", "Duhan", "Casiye", "Ahkaf", "Muhammed", "Fetih", "Hucurat", "Kaf",
    "Zariyat", "Tur", "Necm", "Kamer", "Rahman", "Vakıa", "Hadid", "Mücadele", "Haşr", "Mümtehine",
    "Saf", "Cuma", "Münafikun", "Teğabün", "Talak", "Tahrim", "Mülk", "Kalem", "Hakka", "Mearic",
    "Nuh", "Cin", "Müzzemmil", "Müddessir", "Kıyame", "İnsan", "Mürselat", "Nebe", "Naziat", "Abese",
    "Tekvir", "İnfitar", "Mutaffifin", "İnşikak", "Büruc", "Tarık", "A'la", "Gaşiye", "Fecr", "Beled",
    "Şems", "Leyl", "Duha", "İnşirah", "Tin", "Alak", "Kadir", "Beyyine", "Zilzal", "Adiyat",
    "Karia", "Tekasür", "Asr", "Hümeze", "Fil", "Kureyş", "Maun", "Kevser", "Kafirun", "Nasr",
    "Tebbet", "İhlas", "Felak", "Nas",
]

# Her video aynı görünmesin diye renk teması ayet id'sinden seçilir.
TEMALAR = [
    {"c1": "#0b1d33", "c2": "#10324d", "c3": "#07121f", "glow": "rgba(240,200,120,.22)", "cizgi": "rgba(230,200,140,.10)", "altin": "#f3dc9c"},
    {"c1": "#062a24", "c2": "#0b4237", "c3": "#03140f", "glow": "rgba(220,230,170,.20)", "cizgi": "rgba(210,225,170,.10)", "altin": "#e9d9a0"},
    {"c1": "#1d1233", "c2": "#3a1f4d", "c3": "#0d0818", "glow": "rgba(255,190,140,.22)", "cizgi": "rgba(240,200,170,.10)", "altin": "#f5d3a8"},
    {"c1": "#2a1a0e", "c2": "#4a2e17", "c3": "#140b05", "glow": "rgba(255,215,150,.24)", "cizgi": "rgba(245,210,150,.10)", "altin": "#f7e1b0"},
]


def arapca_rakam(n):
    return str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def json_getir(url, ad):
    yol = CACHE / "api" / f"{ad}.json"
    if not yol.exists():
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(r.text, encoding="utf-8")
    return json.loads(yol.read_text(encoding="utf-8"))


def ayet_getir(sure, no):
    anahtar, dosya = f"{sure}:{no}", f"{sure:03d}{no:03d}"
    ayet = json_getir(f"https://api.quran.com/api/v4/verses/by_key/{anahtar}?words=true&word_fields=text_uthmani",
                      f"kelime/{dosya}")["verse"]
    kelimeler = [w["text_uthmani"] for w in ayet["words"] if w["char_type_name"] == "word"]
    meal = json_getir(f"https://api.alquran.cloud/v1/ayah/{anahtar}/{MEAL[0]}", f"meal/{MEAL[0]}/{dosya}")["data"]["text"]
    return kelimeler, meal


def ses_getir(sure, no, kelime_sayisi):
    """Ayetin tilavet dosyası ve her kelimenin dosya içindeki başlangıç saniyesi."""
    dosya = f"{sure:03d}{no:03d}"
    kayit = json_getir(f"https://api.quran.com/api/v4/recitations/{KARI[0]}/by_ayah/{sure}:{no}?fields=segments",
                       f"segment/{KARI[0]}/{dosya}")["audio_files"][0]
    yol = CACHE / "ses" / str(KARI[0]) / f"{dosya}.mp3"
    if not yol.exists():
        r = requests.get("https://verses.quran.com/" + kayit["url"], timeout=60)
        r.raise_for_status()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(r.content)

    # Segment biçimi: [sıra, kelime_no, başlangıç_ms, bitiş_ms]; bazı kelimeler eksik olabiliyor.
    baslar = [None] * kelime_sayisi
    for s in kayit.get("segments") or []:
        if len(s) >= 4 and 1 <= s[1] <= kelime_sayisi and baslar[s[1] - 1] is None:
            baslar[s[1] - 1] = s[2] / 1000
    onceki = 0.0
    for i, b in enumerate(baslar):
        baslar[i] = onceki = max(b if b is not None else onceki, onceki)
    return yol, baslar


def sure_uzunlugu(dosya):
    # Tahmini "Duration" yerine dosyayı çözüp son zaman damgasını alıyoruz.
    p = subprocess.run([FFMPEG, "-i", str(dosya), "-f", "null", "-"], capture_output=True, text=True)
    s, d, sn = re.findall(r"time=(\d+):(\d+):([\d.]+)", p.stderr)[-1]
    return int(s) * 3600 + int(d) * 60 + float(sn)


def tarayici():
    for aday in (
        os.environ.get("TARAYICI"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
    ):
        if aday and Path(aday).exists():
            return aday
    sys.exit("Chrome/Edge bulunamadı (TARAYICI ortam değişkeniyle verilebilir).")


def html_resim(sablon, veri, png, genislik, yukseklik):
    html = (KOK / "templates" / sablon).read_text(encoding="utf-8")
    html = html.replace("/*DATA*/", json.dumps(veri, ensure_ascii=False))
    html = html.replace("/*FONTS*/", (KOK / "fonts").as_uri() + "/")
    gecici = png.with_suffix(".html")
    gecici.write_text(html, encoding="utf-8")
    subprocess.run([
        tarayici(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={CACHE / 'tarayici-profili'}",
        "--default-background-color=00000000", "--virtual-time-budget=5000",
        f"--window-size={genislik},{yukseklik}", f"--screenshot={png}", gecici.as_uri(),
    ], check=True, capture_output=True)
    gecici.unlink()


def arkaplan_videosu(klip_id):
    """Onaylı kütüphaneden (arkaplanlar.json) klibi bulur, yoksa indirir."""
    import pixabay
    kutuphane = json.loads((KOK / "arkaplanlar.json").read_text(encoding="utf-8"))
    return pixabay.indir(next(k for k in kutuphane if k["id"] == klip_id))


def arkaplan_girdisi(kayit, tema, is_klasoru, toplam, kare):
    """Arka plan için iki ffmpeg girdisi (zemin + yazı gölgesi) ve 1080x1920 rgba [v0] üreten filtre."""
    if kayit.get("arkaplan"):
        # Stok video: dikey kırp, rengini koruyacak kadar hafif karart.
        video = arkaplan_videosu(kayit["arkaplan"])
        zemin = ["-stream_loop", "-1", "-t", f"{toplam:.3f}", "-i", str(video)]
        filtre = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps={FPS},"
                  f"drawbox=c=black@0.15:t=fill,vignette=PI/5,format=rgba[zemin]")
    else:
        png = is_klasoru / "arkaplan.png"
        html_resim("arkaplan.html", {"renkler": tema}, png, 2160, 3840)
        zemin = ["-i", str(png)]
        filtre = (f"[0:v]zoompan=z='1+0.10*on/{kare}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
                  f":d={kare}:s=1080x1920:fps={FPS},format=rgba[zemin]")
    karartma = is_klasoru / "karartma.png"
    html_resim("karartma.html", {}, karartma, 1080, 1920)
    return (zemin + ["-loop", "1", "-t", f"{toplam:.3f}", "-i", str(karartma)],
            filtre + f";[1:v]format=rgba[golge];[zemin][golge]overlay[v0]")


def video_uret(kayit):
    sure, bas, son = kayit["sure"], kayit["bas"], kayit["son"]
    sure_adi = SURELER[sure - 1]
    tema = TEMALAR[int(hashlib.md5(kayit["id"].encode()).hexdigest(), 16) % len(TEMALAR)]
    is_klasoru = CACHE / "is" / kayit["id"]
    if is_klasoru.exists():
        shutil.rmtree(is_klasoru)
    is_klasoru.mkdir(parents=True)

    ayetler = []
    for no in range(bas, son + 1):
        kelimeler, meal = ayet_getir(sure, no)
        ses, kelime_baslari = ses_getir(sure, no, len(kelimeler))
        ayetler.append({"no": no, "kelimeler": kelimeler, "kelime_baslari": kelime_baslari,
                        "meal": meal, "ses": ses, "sure": sure_uzunlugu(ses)})

    # Zaman çizelgesi: her ayetin yazısı kendi tilaveti boyunca ekranda kalır.
    t = BAS_BOSLUK
    for a in ayetler:
        a["ses_bas"] = t
        t += a["sure"]
    toplam = t + SON_BOSLUK
    for i, a in enumerate(ayetler):
        a["bas"] = 0.0 if i == 0 else a["ses_bas"]
        a["son"] = ayetler[i + 1]["ses_bas"] if i + 1 < len(ayetler) else toplam
    kare = round(toplam * FPS)

    # Her ayet için kelime başına bir kare: okunan kelime parlar, okunanlar altın, kalanlar soluk.
    # Kareler concat listesiyle tek bir akışa dizilir; akış zamanı video zamanıyla aynıdır.
    for a in ayetler:
        anlar = [a["bas"]] + [a["ses_bas"] + b for b in a["kelime_baslari"][1:]]
        anlar = [max(anlar[:i + 1]) for i in range(len(anlar))] + [toplam]
        liste = []
        for k in range(len(a["kelimeler"])):
            png = is_klasoru / f"ayet-{a['no']}-{k}.png"
            html_resim("ayet.html", {
                "ust": f"{sure_adi} Suresi · {a['no']}. Ayet",
                "kelimeler": a["kelimeler"],
                "aktif": k,
                "ayet_no": f"﴿{arapca_rakam(a['no'])}﴾",
                "meal": a["meal"],
                "kanal": KANAL,
                "altin": tema["altin"],
            }, png, 1080, 1920)
            sure_sn = anlar[k + 1] - (0 if k == 0 else anlar[k])
            liste += [f"file '{png.as_posix()}'", f"duration {max(sure_sn, 1 / FPS):.3f}"]
        liste.append(liste[-2])  # concat demuxer son dosyanın süresini ancak tekrar edilince uygular
        a["liste"] = is_klasoru / f"ayet-{a['no']}.txt"
        a["liste"].write_text("ffconcat version 1.0\n" + "\n".join(liste) + "\n", encoding="utf-8")

    girdiler, arkaplan_filtresi = arkaplan_girdisi(kayit, tema, is_klasoru, toplam, kare)
    f = [arkaplan_filtresi]
    z = 2   # sıradaki ffmpeg girdi numarası (0-1 arka plan)
    if kayit.get("kanca"):
        # Kanca yalnızca ilk saniyelerde: izleyiciyi durdurur, sonra ekranı ayete bırakır.
        png = is_klasoru / "kanca.png"
        html_resim("kanca.html", {"kanca": kayit["kanca"], "altin": tema["altin"]}, png, 1080, 1920)
        girdiler += ["-loop", "1", "-t", f"{KANCA_SN + 0.1:.3f}", "-i", str(png)]
        f.append(f"[{z}:v]format=rgba,fade=t=out:st={KANCA_SN - 0.5:.3f}:d=0.5:alpha=1[kanca]")
        f.append("[v0][kanca]overlay=eof_action=pass[v0k]")
        z += 1
    for a in ayetler:
        girdiler += ["-f", "concat", "-safe", "0", "-i", str(a["liste"])]
    for a in ayetler:
        girdiler += ["-i", str(a["ses"])]

    n = len(ayetler)
    onceki = "v0k" if kayit.get("kanca") else "v0"
    for i, a in enumerate(ayetler, 1):
        solma = f"fade=t=in:st={a['bas']:.3f}:d={GECIS}:alpha=1," if i > 1 else ""
        f.append(f"[{z + i - 1}:v]fps={FPS},format=rgba,{solma}"
                 f"fade=t=out:st={a['son'] - GECIS:.3f}:d={GECIS}:alpha=1[y{i}]")
        f.append(f"[{onceki}][y{i}]overlay=eof_action=pass:enable='between(t,{a['bas']:.3f},{a['son']:.3f})'[v{i}]")
        onceki = f"v{i}"
    f.append(f"[{onceki}]format=yuv420p[v]")
    sesler = "".join(f"[{z + n + i}:a]" for i in range(n))
    f.append(f"{sesler}concat=n={n}:v=0:a=1,adelay={int(BAS_BOSLUK * 1000)}:all=1,apad,"
             f"afade=t=out:st={toplam - 0.6:.3f}:d=0.6[a]")

    CIKTI.mkdir(exist_ok=True)
    mp4 = CIKTI / f"{kayit['id']}.mp4"
    subprocess.run([
        FFMPEG, "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
        "-t", f"{toplam:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(mp4),
    ], check=True)

    aralik = f"{bas}" if bas == son else f"{bas}-{son}"
    baslik = f"{kayit['baslik']} | {sure_adi} {aralik}"
    aciklama = "\n".join([
        " ".join(a["meal"] for a in ayetler),
        "",
        f"📖 {sure_adi} Suresi, {aralik}. ayet",
        f"🎙️ Kıraat: {KARI[1]}",
        f"📝 Meal: {MEAL[1]}",
        *(["🎞️ Görüntü: Pixabay"] if kayit.get("arkaplan") else []),
        "",
        "Her gün bir ayet için abone olun 🤲",
        "",
        "#shorts #kuran #ayet #dua #kuranıkerim #ayetler",
    ])
    bilgi = {
        "baslik": baslik[:100],
        "aciklama": aciklama,
        "etiketler": ["kuran", "ayet", "kuranı kerim", "dua", "günün ayeti", "shorts",
                      f"{sure_adi} suresi", kayit.get("tema", "")],
        "sure_sn": round(toplam, 2),
    }
    (CIKTI / f"{kayit['id']}.json").write_text(json.dumps(bilgi, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp4, bilgi


if __name__ == "__main__":
    liste = json.loads((KOK / "ayetler.json").read_text(encoding="utf-8"))
    secilen = sys.argv[1] if len(sys.argv) > 1 else liste[0]["id"]
    kayit = next(k for k in liste if k["id"] == secilen)
    mp4, bilgi = video_uret(kayit)
    print(mp4)
    print(json.dumps(bilgi, ensure_ascii=False, indent=2))
