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
| `.github/workflows/gunluk.yml` | Her gün 03:17 UTC `gunluk.py`; Actions sekmesinden elle de (adet/id/gizlilik) çalışır |
| `yayinlananlar.json` | Yüklenenler: `id, video, baslik, gizlilik, tarih` (Actions depoya geri yazar) |
| `yukle.py` | `python yukle.py --giris` izin alır/kanalı gösterir; `python yukle.py out/x.mp4 [--gizlilik private]` yükler |
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

- `.env` → `PIXABAY_KEY=...`
- `client_secret.json` → Google Cloud projesi `manevi-bahcem`, OAuth "Desktop app" istemcisi
- `token.json` → yükleme izni (refresh token). GitHub Actions'ta `YOUTUBE_TOKEN` secret'ı olarak verilir.

Google OAuth uygulaması "In production" ama doğrulanmamış; izin ekranında logo yok (logo eklemek marka doğrulaması
gerektirir, ekleme). Doğrulanmamış API projesinden yüklenen videolar Google audit'i geçene kadar **gizli olarak
kilitlenir** — herkese açık yayın için YouTube API Services Audit başvurusu gerekiyor.

## Durum

- [x] Örnek video (İnşirah 5-8), karaoke + Pixabay arka plan
- [x] Kanal logosu/kapak, YouTube API bağlantısı, ilk gizli yükleme (2026-10-23)
- [~] Onay sayfası **MB-R1** yayında: https://claude.ai/artifact/Pa6GN6Bwb2dbrFn9r2C8or — 66 ayet + 63 klip
  (reviewbot kiti; kaynak `review/`: `hazirla.py` → `review.json`, `refs.json` numaraları tutar). Kullanıcı "bitti"
  deyince: ArtifactData `list` (collection `answers`, `out_dir`) + reviewbot `answers.py`; onaylananlar →
  `ayetler.json` (ayetlere tema uyan klip `arkaplan` olarak atanır) ve `arkaplanlar.json`.
  - 2026-10-23: ayet kartları 1–22 onaylandı → `ayetler.json`'a eklendi. Kart 23–66 ve **63 klibin hiçbiri** henüz
    cevaplanmadı; şimdilik tek onaylı klip (328740) temasına uyan 9 ayette, diğerleri renkli zeminle üretilir.
- [~] GitHub Actions kuruldu (`gunluk.yml`); çalışması için depo secret'ı `YOUTUBE_TOKEN` (= `token.json` içeriği)
  eklenmeli. Claude bulut oturumunun ağı api.quran.com'u engelliyor — videolar burada değil Actions'ta üretilir.
- [ ] YouTube API audit başvurusu (videolar herkese açık olabilsin)
- [ ] Sonra: Günün Hadisi serisi, Instagram/TikTok'a da paylaşım
