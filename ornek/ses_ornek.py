"""Türkçe seslendirme örnekleri: İnşirah 5-8. Meal metni API'den gelir, elle yazılmaz."""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import requests

CIKTI = Path(__file__).parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
SURE, AYETLER = 94, range(5, 9)


def birlestir(parcalar, hedef):
    liste = CIKTI / "liste.txt"
    liste.write_text("".join(f"file '{p.resolve()}'\n" for p in parcalar))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
                    "-ac", "1", "-b:a", "128k", str(hedef)], check=True)
    liste.unlink()
    for p in parcalar:
        p.unlink()


# A) Diyanet Vakfı meal kaydı (alquran.cloud tr.vakfi-audio)
parcalar = []
for no in AYETLER:
    d = requests.get(f"https://api.alquran.cloud/v1/ayah/{SURE}:{no}/tr.vakfi-audio", timeout=30).json()["data"]
    p = CIKTI / f"a{no}.mp3"
    p.write_bytes(requests.get(d["audio"], timeout=60).content)
    parcalar.append(p)
birlestir(parcalar, CIKTI / "A-diyanet-vakfi-kaydi.mp3")

# B) Elmalılı meali (tr.yazir) yapay zekâ sesleriyle
meal = " ".join(requests.get(f"https://api.alquran.cloud/v1/ayah/{SURE}:{no}/tr.yazir", timeout=30).json()["data"]["text"]
                for no in AYETLER)
(CIKTI / "meal.txt").write_text(meal + "\n", encoding="utf-8")

# B) Piper: açık kaynak, bilgisayarda çalışan erkek sesleri (kadın sesi yok — kullanıcı kararı)
REV = "https://huggingface.co/rhasspy/piper-voices/resolve/2083514c726ed4e54d15dbf8d86285d6059642f0/tr/tr_TR"
for ses in ["fettah", "fahrettin"]:
    try:
        model = CIKTI / "tr.onnx"
        taban = f"{REV}/{ses}/medium/tr_TR-{ses}-medium.onnx"
        model.write_bytes(requests.get(taban, timeout=180).content)
        Path(str(model) + ".json").write_bytes(requests.get(taban + ".json", timeout=60).content)
        if model.stat().st_size < 1_000_000:
            raise RuntimeError("model inmedi: " + model.read_text()[:80])
        wav = CIKTI / "p.wav"
        subprocess.run([sys.executable, "-m", "piper", "-m", str(model), "-f", str(wav)],
                       input=meal.encode(), check=True)
        birlestir([wav], CIKTI / f"B-{ses}.mp3")
    except Exception as hata:
        print(ses, "olmadı:", hata)
    finally:
        for f in (CIKTI / "tr.onnx", CIKTI / "tr.onnx.json"):
            f.unlink(missing_ok=True)
