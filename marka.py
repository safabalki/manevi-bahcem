"""Kanal logosunu (800x800) ve kapak görselini (2560x1440) out/marka/ altına üretir."""
from shorts import CIKTI, html_resim

klasor = CIKTI / "marka"
klasor.mkdir(parents=True, exist_ok=True)
logo = klasor / "logo.png"
html_resim("logo.html", {}, logo, 800, 800)
html_resim("kapak.html", {"logo": logo.as_uri()}, klasor / "kapak.png", 2560, 1440)
print(klasor)
