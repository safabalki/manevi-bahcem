"""Zamanlanmış çalışmada şimdi kaç video yüklenmeli? (yalnızca standart kütüphane)

GitHub cron'u geciktirebiliyor ya da hiç çalıştırmıyor; bu yüzden workflow her saat çalışır ve bu betik
"bugün (Türkiye saati) şu ana kadar kaç video çıkmalıydı" ile "kaç çıktı"yı karşılaştırır. Eksik varsa 1 döner.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAATLER = (7, 13, 19)   # Türkiye saatiyle yayın saatleri
TR = timezone(timedelta(hours=3))

simdi = datetime.now(TR)
yol = Path(__file__).resolve().parent / "yayinlananlar.json"
yayinlanan = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else []
bugun = sum(datetime.fromisoformat(y["tarih"]).astimezone(TR).date() == simdi.date() for y in yayinlanan)
gereken = sum(simdi.hour >= s for s in SAATLER)
print(f"{simdi:%Y-%m-%d %H:%M} TR · bugün yüklenen {bugun} · bu saate kadar gereken {gereken}", file=sys.stderr)
print(1 if bugun < gereken else 0)
