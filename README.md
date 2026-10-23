# Manevi Bahçem — Kur'an Shorts

Her gün seçme ayetlerden dikey YouTube Shorts üretip **Manevi Bahçem** kanalına yükler.
Proje kararları ve durumu: [CLAUDE.md](CLAUDE.md).

## Yeni bilgisayarda kurulum

Gerekenler: Git, Python 3.12+, Microsoft Edge veya Google Chrome, Claude Code.

```powershell
git clone https://github.com/safabalki/manevi-bahcem.git
cd manevi-bahcem
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Sonra yedekten şu üç gizli dosyayı proje klasörüne kopyalayın (depoda yoklar):

- `.env`
- `client_secret.json`
- `token.json`

Kontrol:

```powershell
.\.venv\Scripts\python.exe yukle.py --giris      # "Bağlı kanal: Manevi Bahçem" yazmalı
.\.venv\Scripts\python.exe shorts.py             # out\ klasörüne örnek video üretir
```

`token.json` kaybolursa `client_secret.json` ile `yukle.py --giris` çalıştırıp yeniden izin verin
(hesap seçiminde **Manevi Bahçem**'i seçin).
