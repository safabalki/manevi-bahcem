"""Şimdi bir eski video (Instagram/Facebook doldurma) paylaşılmalı mı? (yalnızca standart kütüphane)

GitHub, yeni eklenen günde iki kez çalışan zamanlamayı hiç tetiklemedi; bu yüzden workflow her saat çalışır ve
bu betik "akşam (TR 20-23) ve bugün 2'den az eski video paylaşıldıysa" 1, değilse 0 yazar.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

GUNLUK = 2
SAATLER = range(20, 24)   # Türkiye saatiyle
TR = timezone(timedelta(hours=3))

simdi = datetime.now(TR)
yol = Path(__file__).resolve().parent / "yayinlananlar.json"
kayitlar = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else []
# Bugün en az bir platforma "gecmis" olarak giden video sayısı.
bugun = sum(any(k.get(p, {}).get("gecmis") and k[p].get("tarih") == simdi.date().isoformat()
                for p in ("instagram", "facebook")) for k in kayitlar)
print(f"{simdi:%Y-%m-%d %H:%M} TR · bugün eski video {bugun}/{GUNLUK}", file=sys.stderr)
print(1 if simdi.hour in SAATLER and bugun < GUNLUK else 0)
