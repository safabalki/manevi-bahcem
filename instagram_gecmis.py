"""Instagram ve Facebook'u doldurur: YouTube'a daha önce yüklenmiş ama oralara gitmemiş videoları Reels olarak paylaşır.

En çok izlenenler önce gider. YouTube'da silinmiş (ör. telif uyarısı yüzünden kullanıcının sildiği), herkese açık
olmayan ya da bölge engelli videolar atlanır. Video yeniden üretilir (out/ Actions'ta kalıcı değil); kaynak, metin
ve klip aynı olduğu için içerik aynıdır. Sonuç yayinlananlar.json'daki ilgili kayda "instagram"/"facebook" olarak
yazılır; hata almış platform sonraki çalışmada yeniden denenir.

Kullanım:
  python instagram_gecmis.py --adet 2
  python instagram_gecmis.py --liste      # yalnızca sırayı göster
"""
import argparse
import json

import analiz
import facebook
import instagram
import shorts
import yukle
from gunluk import EN_UZUN_SN, YAYINLANANLAR, oku, KOK

PLATFORMLAR = {"instagram": instagram.yukle, "facebook": facebook.yukle}


def eksik(kayit, acik):
    """Bu kayıt hangi platformlara henüz (başarıyla) gitmedi?"""
    return [p for p in acik if p not in kayit or "hata" in kayit[p]]


def sira(yt, acik):
    yayinlanan = oku(YAYINLANANLAR, [])
    bekleyen = [y for y in yayinlanan if "video" in y and y.get("gizlilik") == "public" and eksik(y, acik)]
    ist = analiz.istatistikler(yt, [y["video"] for y in bekleyen])
    uygun = [y for y in bekleyen if y["video"] in ist and ist[y["video"]]["gizlilik"] == "public"
             and not ist[y["video"]]["engel"]]
    atlanan = [y["id"] for y in bekleyen if y not in uygun]
    uygun.sort(key=lambda y: -ist[y["video"]]["izlenme"])
    return uygun, atlanan, ist


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--adet", type=int, default=1)
    p.add_argument("--liste", action="store_true")
    a = p.parse_args()

    acik = ["instagram"] + (["facebook"] if facebook.acik() else [])
    yt = yukle.youtube()
    uygun, atlanan, ist = sira(yt, acik)
    print(f"Açık platformlar: {acik}; gidecek {len(uygun)} video; atlanan (silinmiş/gizli/engelli): {atlanan or 'yok'}")
    for y in uygun:
        print(f"  {ist[y['video']]['izlenme']:>7,}  {y['id']}  → {', '.join(eksik(y, acik))}")
    if a.liste:
        raise SystemExit

    ayetler = {k["id"]: k for k in oku(KOK / "ayetler.json", [])}
    hata_var = False
    for y in uygun[:a.adet]:
        mp4, bilgi = shorts.video_uret(ayetler[y["id"]])
        if bilgi["sure_sn"] > EN_UZUN_SN:
            print(f"Atlandı (uzun): {y['id']}")
            continue
        sonuclar = {}
        for platform in eksik(y, acik):
            try:
                mid, link = PLATFORMLAR[platform](mp4, bilgi)
                sonuclar[platform] = {"id": mid, "link": link, "gecmis": True}
                print(f"{platform}: paylaşıldı {y['id']} {link or mid}")
            except Exception as hata:
                sonuclar[platform] = {"hata": str(hata)[:300], "gecmis": True}
                hata_var = True
                print(f"{platform} hatası ({y['id']}): {hata}")
        # Her videodan sonra yaz; dosyayı yeniden okuyup yalnızca bu kaydı güncelle.
        kayitlar = oku(YAYINLANANLAR, [])
        for k in kayitlar:
            if k.get("video") == y["video"]:
                k.update(sonuclar)
        YAYINLANANLAR.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if hata_var:
            break
