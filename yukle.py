"""YouTube'a video yükler.

İlk çalıştırmada tarayıcıda izin istenir ve token.json oluşur; sonraki çalıştırmalar
(GitHub Actions dahil) bu token'ı kullanır.

Kullanım:
  python yukle.py --giris                 # sadece izin al, bağlı kanalı göster
  python yukle.py out/insirah-5-8.mp4     # yanındaki .json'daki başlık/açıklamayla yükle
"""
import argparse
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

KOK = Path(__file__).resolve().parent
IZINLER = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
KATEGORI_EGITIM = "27"


def youtube():
    token = KOK / "token.json"
    # GitHub Actions'ta token dosya yerine Secrets'tan ortam değişkeni olarak gelir.
    if os.environ.get("YOUTUBE_TOKEN"):
        kimlik = Credentials.from_authorized_user_info(json.loads(os.environ["YOUTUBE_TOKEN"]), IZINLER)
    elif os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        # Telefondan (OAuth Playground) alınan token: JSON yazmadan üç ayrı secret yeter.
        kimlik = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                             token_uri="https://oauth2.googleapis.com/token",
                             client_id=os.environ["YOUTUBE_CLIENT_ID"],
                             client_secret=os.environ["YOUTUBE_CLIENT_SECRET"], scopes=IZINLER)
    elif token.exists():
        kimlik = Credentials.from_authorized_user_file(str(token), IZINLER)
    else:
        akis = InstalledAppFlow.from_client_secrets_file(str(KOK / "client_secret.json"), IZINLER)
        # Tarayıcı her ortamda kendiliğinden açılmıyor; bağlantıyı yazdırıp elle açtırıyoruz.
        kimlik = akis.run_local_server(port=8765, prompt="consent", open_browser=False,
                                       authorization_prompt_message="Bu bağlantıyı tarayıcıda açın:\n{url}")
        token.write_text(kimlik.to_json(), encoding="utf-8")
    if not kimlik.valid:
        kimlik.refresh(Request())
    return build("youtube", "v3", credentials=kimlik)


def kanal_bilgisi(yt):
    k = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    return k["id"], k["snippet"]["title"], k["snippet"].get("customUrl", "")


def yukle(yt, mp4, bilgi, gizlilik="private"):
    istek = yt.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": bilgi["baslik"],
                "description": bilgi["aciklama"],
                "tags": [e for e in bilgi["etiketler"] if e],
                "categoryId": KATEGORI_EGITIM,
                "defaultLanguage": "tr",
                "defaultAudioLanguage": "ar",
            },
            "status": {
                "privacyStatus": gizlilik,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": False,
            },
        },
        media_body=MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True, chunksize=8 << 20),
    )
    cevap = None
    while cevap is None:
        _, cevap = istek.next_chunk()
    return cevap["id"]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video", nargs="?")
    p.add_argument("--giris", action="store_true")
    p.add_argument("--gizlilik", default="private", choices=["private", "unlisted", "public"])
    a = p.parse_args()

    yt = youtube()
    kid, ad, adres = kanal_bilgisi(yt)
    print(f"Bağlı kanal: {ad} {adres} ({kid})")
    if a.video:
        mp4 = Path(a.video)
        bilgi = json.loads(mp4.with_suffix(".json").read_text(encoding="utf-8"))
        vid = yukle(yt, mp4, bilgi, a.gizlilik)
        print(f"Yüklendi: https://youtube.com/shorts/{vid}")
