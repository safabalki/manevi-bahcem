"""Haftalık analiz şimdi çalışmalı mı? (yalnızca standart kütüphane) Pazar TR 21:00 sonrası ve son rapor 6 günden eskiyse 1."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
simdi = datetime.now(TR)
klasor = Path(__file__).resolve().parent / "rapor"
tarihler = sorted(p.stem for p in klasor.glob("20??-??-??.md")) if klasor.exists() else []
son = datetime.fromisoformat(tarihler[-1]).replace(tzinfo=TR) if tarihler else None
gerek = simdi.weekday() == 6 and simdi.hour >= 21 and (son is None or simdi - son > timedelta(days=6))
print(f"{simdi:%Y-%m-%d %H:%M} TR · son rapor {son and son.date()}", file=sys.stderr)
print(1 if gerek else 0)
