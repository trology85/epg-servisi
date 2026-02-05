import requests
import gzip
import io
import re
from datetime import datetime, timedelta

# 1. SAAT KAYDIRMA FONKSİYONU (EKSİKSİZ)
def offset_time(xml_fragment, hours_to_add):
    # EPG saat formatını (20260205053000 +0000) bulup kaydırır
    time_pattern = r'(\d{14})\s\+\d{4}'
    def shift_match(match):
        time_str = match.group(1)
        dt = datetime.strptime(time_str, "%Y%m%d%H%M%S")
        new_dt = dt + timedelta(hours=hours_to_add)
        # Türkiye saati olan +0300 olarak mühürler
        return new_dt.strftime("%Y%m%d%H%M%S") + " +0300"
    return re.sub(time_pattern, shift_match, xml_fragment)

# 2. ANA GÜNCELLEME FONKSİYONU (EKSİKSİZ)
def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    rich_url = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Kaynaklar indiriliyor...")
        # Ana Liste İndirme (Saatleri doğru olan TR1)
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_main = f.read().decode('utf-8')

        # Zengin Liste İndirme (DMAX ve TRT 2'nin detaylı olduğu yer)
        resp_rich = requests.get(rich_url, timeout=30)
        resp_rich.encoding = 'utf-8'
        xml_rich = resp_rich.text

        # --- DMAX ÖZEL MÜDAHALE ---
        print("2. DMAX verisi 'saat düzeltilerek' hazırlanıyor...")
        dmax_pattern = r'<programme[^>]+channel="DMAX".*?</programme>'
        dmax_matches = re.findall(dmax_pattern, xml_rich, flags=re.DOTALL)
        
        dmax_data = ""
        for m in dmax_matches:
            # İsmi DMAX.HD.tr yap ve saati 3 saat ileri al
            fixed = m.replace('channel="DMAX"', 'channel="DMAX.HD.tr"')
            fixed = offset_time(fixed, 3) 
            dmax_data += fixed + "\n"

        # --- FOX -> NOW DÖNÜŞÜMÜ ---
        xml_main = xml_main.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"').replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')
        
        # --- ÇAKIŞMA ENGELLEME ---
        # Ana listede (TR1) DMAX verisi varsa sil ki 'çift program' görünmesin
        xml_main = re.sub(r'<programme[^>]+channel="DMAX.HD.tr".*?</programme>', '', xml_main, flags=re.DOTALL)

        # --- BİRLEŞTİRME ---
        # Hazırladığımız temiz DMAX verisini ana dosyanın sonuna ekle
        final_xml = xml_main.replace("</tv>", dmax_data + "</tv>")

        # DOSYAYI KAYDET (Karakter sorunu olmaması için utf-8-sig)
        with open("epg.xml", "w", encoding="utf-8-sig") as f:
            f.write(final_xml)
            
        print("--- BAŞARILI: Tüm düzenlemeler tek dosyada birleşti! ---")

    except Exception as e:
        print(f"Hata oluştu: {e}")

# 3. KODU ÇALIŞTIRAN KISIM (EKSİKSİZ)
if __name__ == "__main__":
    update_epg()
