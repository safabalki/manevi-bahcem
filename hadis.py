"""Günün Hadisi: HadeethEnc'ten (hadeethenc.com) alınan sahih hadisle dikey Shorts üretir.

Hadis metni, Türkçe tercümesi, derecesi ve kaynağı yalnızca HadeethEnc API'sinden gelir; hiçbir hadis metni burada
yazılmaz, üretilmez ya da değiştirilmez. Metin yalnızca görsel olarak bölünür (râvi cümlesi / «...» içindeki söz).
Derecesi "Sahih" olmayan hadis reddedilir. Ses: telifsiz doğa sesi (sesler/KAYNAK.md), müzik yok.

Kullanım:
  python hadis.py 5351                       # HadeethEnc hadis id → out/hadis-5351.mp4 + .json
  python hadis.py 5351 --kanca "..." --arkaplan 328740
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import shorts
from shorts import CACHE, CIKTI, FFMPEG, FPS, KANAL, KANCA_SN, TEMALAR, arkaplan_girdisi, html_resim, json_getir

KOK = Path(__file__).resolve().parent
SES = KOK / "sesler" / "dere.ogg"
API = "https://hadeethenc.com/api/v1/hadeeths/one/?language=tr&id={}"
SAYFA = "https://hadeethenc.com/tr/browse/hadith/{}"


def hadis_getir(hid):
    h = json_getir(API.format(hid), f"hadis/tr/{hid}")
    if not h.get("grade", "").startswith("Sahih") or not h.get("grade_ar", "").startswith("صحيح"):
        raise SystemExit(f"Hadis {hid} sahih değil ({h.get('grade')}); kullanılmaz.")
    return h


def bol(metin, acilis="«", kapanis="»"):
    """'Râvi ... şöyle buyurmuştur: «söz»' → (râvi cümlesi, «söz»). Metin değişmez, yalnızca ikiye ayrılır."""
    i = metin.find(acilis)
    if i <= 0 or kapanis not in metin[i:]:
        return "", metin.strip()
    return metin[:i].strip(), metin[i:].strip()


def video_uret(hid, kanca=None, arkaplan=None):
    h = hadis_getir(hid)
    ravi, soz = bol(h["hadeeth"])
    _, soz_ar = bol(h["hadeeth_ar"])
    tema = TEMALAR[int(hid) % len(TEMALAR)]
    kelime = len(re.findall(r"\w+", soz)) + len(re.findall(r"\w+", ravi)) // 2
    toplam = max(16.0, min(42.0, 5.0 + kelime / 2.2))
    kare = round(toplam * FPS)
    is_klasoru = CACHE / "is" / f"hadis-{hid}"
    is_klasoru.mkdir(parents=True, exist_ok=True)

    kart = is_klasoru / "kart.png"
    html_resim("hadis.html", {
        "arapca": soz_ar, "ravi": ravi, "metin": soz, "altin": tema["altin"], "kanal": KANAL,
        "derece": f"{h['grade']} · {h['attribution']}", "kaynak": f"Kaynak: HadeethEnc.com · #{hid}",
    }, kart, 1080, 1920)

    girdiler, f0 = arkaplan_girdisi({"id": f"hadis-{hid}", "arkaplan": arkaplan}, tema, is_klasoru, toplam, kare)
    f = [f0]
    z = 2
    kart_bas = 0.4
    if kanca:
        png = is_klasoru / "kanca.png"
        html_resim("kanca.html", {"kanca": kanca, "altin": tema["altin"]}, png, 1080, 1920)
        girdiler += ["-loop", "1", "-t", f"{KANCA_SN + 0.1:.3f}", "-i", str(png)]
        f.append(f"[{z}:v]format=rgba,fade=t=out:st={KANCA_SN - 0.5:.3f}:d=0.5:alpha=1[kanca]")
        f.append("[v0][kanca]overlay=eof_action=pass[v0k]")
        z += 1
        kart_bas = KANCA_SN - 0.4
    girdiler += ["-loop", "1", "-t", f"{toplam:.3f}", "-i", str(kart)]
    f.append(f"[{z}:v]format=rgba,fade=t=in:st={kart_bas:.3f}:d=0.8:alpha=1,"
             f"fade=t=out:st={toplam - 0.7:.3f}:d=0.6:alpha=1[kart]")
    f.append(f"[{'v0k' if kanca else 'v0'}][kart]overlay[vk]")
    f.append("[vk]format=yuv420p[v]")
    z += 1
    girdiler += ["-stream_loop", "-1", "-i", str(SES)]
    f.append(f"[{z}:a]volume=2.0,afade=t=in:st=0:d=1.2,afade=t=out:st={toplam - 1.5:.3f}:d=1.5[a]")

    CIKTI.mkdir(exist_ok=True)
    ad = f"hadis-{hid}"
    mp4 = CIKTI / f"{ad}.mp4"
    subprocess.run([
        FFMPEG, "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
        "-t", f"{toplam:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(mp4),
    ], check=True)

    baslik = f"{h['title']}"
    if len(baslik) > 78:
        baslik = baslik[:75].rsplit(" ", 1)[0] + "…"
    aciklama = "\n".join([
        h["hadeeth"], "",
        f"📚 {h['grade']} · {h['attribution']}",
        f"🔗 Kaynak: {SAYFA.format(hid)}", "",
        "💬 Bu hadisten ne anladın? Yorumlara yaz 🤲", "",
        "Her gün bir hadis için abone olun 🤲", "",
        "#shorts #hadis #gününhadisi #sünnet #islam",
    ])
    bilgi = {"baslik": f"{baslik} | Günün Hadisi"[:100], "aciklama": aciklama,
             "etiketler": ["hadis", "günün hadisi", "sahih hadis", "sünnet", "islam", "shorts"],
             "sure_sn": round(toplam, 2), "kaynak": SAYFA.format(hid)}
    (CIKTI / f"{ad}.json").write_text(json.dumps(bilgi, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp4, bilgi


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("id")
    p.add_argument("--kanca")
    p.add_argument("--arkaplan", type=int)
    a = p.parse_args()
    mp4, bilgi = video_uret(a.id, a.kanca, a.arkaplan)
    print(mp4)
    print(json.dumps(bilgi, ensure_ascii=False, indent=2))
