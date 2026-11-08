# Manevi Bahçem — Kur'an Shorts otomasyonu

YouTube kanalı **Manevi Bahçem** (@manevibahcem, kanal id `UCjPVcmgjAKGRXcTq7EfMhrg`, marka hesabı) için her gün
seçme ayetlerden dikey Shorts üretip yükleyen sistem. Kullanıcının hedefi: çok izlenmek. Kullanıcıyla **Türkçe** konuş.

## Değişmez içerik kuralları

- **Kur'an metnini, meali veya hadisi asla yapay zekâyla üretme ya da elle yazma.** Arapça kelimeler, tilavet ve kelime
  zamanlamaları api.quran.com'dan (recitation 7 = Alafasy), meal api.alquran.cloud'dan (`tr.yazir`, Elmalılı — telif
  serbest; Diyanet meali telifli) gelir. Kendi tefsir/yorumunu ekleme.
- Peygamber, melek, sahabe tasviri yok. Arka planlar yalnızca insansız doğa/mimari görüntüler.
- Arka plan klipleri yalnızca kullanıcının onayladığı `arkaplanlar.json` kütüphanesinden seçilir; otomatik aramadan
  gelen klip doğrudan yayına girmez (uygunsuz görüntü riski).
- Ayet listesi (`ayetler.json`) — başlık ve kanca cümlesi dahil — kullanıcı onayından geçer. Kancalar saygılı olur,
  "izlemeyen pişman olur" tarzı tık tuzağı yok.
- İleride: "Günün Hadisi" yalnızca derecesi belirtilmiş kaynaktan (HadeethEnc), kaynak gösterilerek; "Dinin Temelleri"
  tam otomatik değil, metni kullanıcı/hoca onaylar.

## Kullanıcının verdiği kararlar

- Tek kanal, birden fazla seri (Günün Ayeti şimdi; hadis, dinin temelleri, dualar sonra).
- Türkçe seslendirme denenecekse **kadın sesi yok** (2026-10-25). Ses örnekleri dalı: `claude/ses-ornekleri`.
- **Telif:** Alafasy tilavetinde Content ID hak talebi var (Alfan Music / I-Media Production). YouTube hak talepli
  **1 dakikadan uzun** Shorts'u dünya genelinde engelliyor (Haşr 22-24, Nur 35 — kullanıcı sildi). `gunluk.py`
  58 sn üstünü yüklemez, `yayinlananlar.json`'a `atlandi` yazar. Kullanıcı telif uyarısı gelen videoyu siler, TikTok'a da koymaz.
- Format: dikey Shorts, 15–45 sn, kelime kelime karaoke vurgusu, sinematik doğa arka planı, kanca yazısı yalnızca ilk 3 sn.
- **Türkçe seslendirme istemedi** (TTS denendi, "soyut kaldı") — yalnızca Arapça tilavet.
- Tam animasyon/AI video yok.
- Zamanlama: GitHub Actions (gizli depo), her gece.
- Pexels yeni API anahtarı vermiyor → Pixabay kullanılıyor.

## Dosyalar

| Dosya | Görev |
|---|---|
| `shorts.py` | `python shorts.py [ayet-id]` → `out/<id>.mp4` + `out/<id>.json` (başlık/açıklama/etiket) |
| `gunluk.py` | Sıradaki (yüklenmemiş) ayeti üretir + yükler, `yayinlananlar.json`'a yazar; `--adet`, `--id`, `--sadece-uret` |
| `.github/workflows/gunluk.yml` | Her saat çalışır; `sira.py` bugün TR 07/13/19 yayınlarından eksik varsa 1 video üretir (GitHub cron'u gecikip atlayabiliyor); Actions sekmesinden elle de (adet/id/gizlilik) çalışır |
| `yayinlananlar.json` | Yüklenenler: `id, video, baslik, gizlilik, tarih` (Actions depoya geri yazar) |
| `yukle.py` | `python yukle.py --giris` izin alır/kanalı gösterir; `python yukle.py out/x.mp4 [--gizlilik private]` yükler |
| `tiktok.py` | TikTok Content Posting API: `--bagla KOD`, `--bilgi`, `out/x.mp4`; token şifreli `tiktok-token.enc` (anahtar = SHA256(`TIKTOK_CLIENT_SECRET`)), her yenilemede güncellenir |
| `.github/workflows/tiktok-bagla.yml` | Elle: tiktok.html'in verdiği kodla hesabı bağlar, isterse gizli deneme videosu yükler |
| `instagram.py` | Instagram Reels (Graph API, Facebook Login yolu → dosya rupload.facebook.com'a yüklenir): `--bagla KISA_TOKEN`, `--bilgi`, `out/x.mp4`; süresiz Sayfa token'ı şifreli `instagram-token.enc` (anahtar = SHA256(`INSTAGRAM_APP_SECRET`)) |
| `.github/workflows/instagram-bagla.yml` | Elle: Graph API Explorer'daki kısa ömürlü token'la hesabı bağlar, isterse deneme Reels'i paylaşır |
| `pixabay.py` | `python pixabay.py "sorgu" [adet]` → `cache/pixabay-adaylar.json`'a aday ekler; `indir()` klibi önbelleğe alır |
| `marka.py` | Logo (800x800) ve kapak (2560x1440) → `out/marka/` |
| `ayetler.json` | Seçme ayetler: `id, sure, bas, son, baslik, kanca, tema, arkaplan(klip id)` |
| `arkaplanlar.json` | Onaylı Pixabay klipleri: `id, url, sayfa, etiketler, temalar` |
| `templates/` | HTML şablonları; Edge/Chrome headless ile PNG'ye çevrilir (Arapça harekeler için tarayıcı şart) |
| `site/` | safabalki.github.io'daki ana sayfa + gizlilik politikası (OAuth için gerekli; ayrı public depoda yayında) |

Teknik notlar: ffmpeg `imageio-ffmpeg` paketinden gelir (sisteme kurulu değil). Tarayıcı yolu `TARAYICI` ortam
değişkeniyle verilebilir; yoksa Edge → Chrome → google-chrome aranır. Yazılar YouTube arayüzünün kapladığı alanlardan
(üst ~220px, alt ~480px, sağ ~150px) uzak tutulur.

## Gizli bilgiler (depoda YOK, .gitignore'da)

- `.env` → `PIXABAY_KEY=...` (yalnızca yeni klip adayı aramak için; video üretimi klibi CDN adresinden anahtarsız indirir)
- `client_secret.json` → Google Cloud projesi `manevi-bahcem`, OAuth "Desktop app" istemcisi
- `token.json` → yükleme izni (refresh token). GitHub Actions'ta `YOUTUBE_TOKEN` secret'ı olarak verilir; ya da
  (telefondan OAuth Playground ile alınmışsa) `YOUTUBE_REFRESH_TOKEN` + `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET`.

Google OAuth uygulaması "In production" ama doğrulanmamış; izin ekranında logo yok (logo eklemek marka doğrulaması
gerektirir, ekleme). Doğrulanmamış projelerde videolar normalde gizli kilitlenir, ama 2026-10-24'te kullanıcı API ile
yüklenenleri Studio'dan herkese açık yapabildi → Actions artık `public` yüklüyor. Audit başvurusu yine de yapılacak.

## Durum

- [x] Örnek video (İnşirah 5-8), karaoke + Pixabay arka plan
- [x] Kanal logosu/kapak, YouTube API bağlantısı, ilk gizli yükleme (2026-10-23)
- [~] Onay sayfası **MB-R1** yayında: https://claude.ai/artifact/Pa6GN6Bwb2dbrFn9r2C8or — 66 ayet + 63 klip
  (reviewbot kiti; kaynak `review/`: `hazirla.py` → `review.json`, `refs.json` numaraları tutar). Kullanıcı "bitti"
  deyince: ArtifactData `list` (collection `answers`, `out_dir`) + reviewbot `answers.py`; onaylananlar →
  `ayetler.json` (ayetlere tema uyan klip `arkaplan` olarak atanır) ve `arkaplanlar.json`.
  - 2026-10-23: kullanıcı sohbette **66 ayetin ve 63 klibin hepsini** onayladı → `ayetler.json`, `arkaplanlar.json`.
    Klipler temaya göre, en az kullanılan önce olacak şekilde dağıtıldı (yayınlanmış ayetin klibi değişmez). MB-R1 tamam.
- [x] GitHub Actions çalışıyor (secret'lar: `YOUTUBE_REFRESH_TOKEN/CLIENT_ID/CLIENT_SECRET`, Web istemcisi + OAuth
  Playground). İlk otomatik yükleme 2026-10-23 (İnşirah 5-8). API kotası 10.000/gün, yükleme 1.600 → en çok 6 video/gün. Claude bulut oturumunun ağı api.quran.com'u engelliyor — videolar burada değil Actions'ta üretilir.
- [ ] YouTube API audit başvurusu (videolar herkese açık olabilsin)
- [~] TikTok (@manevibahcem): geliştirici uygulaması açıldı, secret'lar `TIKTOK_CLIENT_KEY/SECRET` girildi. Site:
  `kosullar.html`, `tiktok.html` (Client Key girilir → TikTok izni → kod). `gunluk.py` YouTube'dan sonra TikTok'a da
  yükler (token varsa; hata YouTube'u durdurmaz). Sandbox bağlandı 2026-10-24; denetimsiz uygulama herkese açık
  hesaba Direct Post yapamıyor (`unaudited_client_can_only_post_to_private_accounts`) → video **taslak** olarak TikTok
  gelen kutusuna gider, kullanıcı uygulamadan paylaşır (açıklamayı kendisi yazar). Production başvurusu yalnızca `user.info.basic` + `video.upload`
  (taslak) ile; Direct Post (`video.publish`) sonra ayrı audit. Onaylanınca secret'lar production key/secret'a çevrilip
  tiktok.html'den yeniden bağlanılır. Claude oturumundan open.tiktokapis.com engelli; test Actions'ta.
- [~] TikTok production onaylandı (2026-11-08, yalnızca `user.info.basic` + `video.upload` → hâlâ açıklamasız taslak).
  Canlı key/secret girilince eski `tiktok-token.enc` çözülemez (anahtar secret'tan türetiliyor) → tiktok.html'den
  canlı Client Key ile yeniden bağlanmalı. Açıklamalı otomatik paylaşım `video.publish` + Direct Post audit ister;
  TikTok kişisel/iç kullanım uygulamalarını genelde onaylamıyor. Kod hazır: token'da `video.publish` varsa Direct Post dener.
- [~] Instagram: `instagram.py` yazıldı (2026-11-08), henüz bağlanmadı. Gerekenler: profesyonel IG hesabı + bağlı
  Facebook Sayfası, Meta geliştirici uygulaması (kendi hesabı için App Review gerekmez), secret'lar
  `INSTAGRAM_APP_ID/SECRET`, sonra "Instagram Bağla" workflow'u. `gunluk.py` yalnızca `public` yüklemelerde paylaşır;
  hata YouTube'u durdurmaz.
- [ ] Sonra: Günün Hadisi serisi
