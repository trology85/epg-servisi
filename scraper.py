import requests
import gzip
import io
import re

def update_epg():
    # 1. Doğru saatlerin olduğu ana kaynak
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    # 2. Açıklamaların olduğu zengin kaynak
    rich_url = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Dosyalar indiriliyor...")
        # Ana kaynak (Gzip)
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_main = f.read().decode('utf-8')
        
        # Zengin kaynak (Düz XML)
        resp_rich = requests.get(rich_url, timeout=60)
        resp_rich.encoding = 'utf-8'
        xml_rich = resp_rich.text

        # --- ADIM 1: FOX -> NOW DEĞİŞİMİ ---
        xml_main = xml_main.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"').replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        print("2. Özel kanallar için açıklamalar 'tr.xml'den sökülüyor...")
        
        # Sadece bu kanalların verilerini Zengin Kaynaktan alacağız
        # Soldaki XML'deki orijinal ID, Sağdaki senin sistemindeki ID
        special_channels = {
            "CNBC-e": "CNBC-E",
            "DMAX": "DMAX.HD.tr",
            "TRT 2": "TRT2.tr"
        }

        rich_programmes = ""
        for source_id, target_id in special_channels.items():
            # Regex ile zengin dosyadan ilgili kanalı bul
            pattern = rf'<programme[^>]+channel="{re.escape(source_id)}".*?</programme>'
            matches = re.findall(pattern, xml_rich, flags=re.DOTALL)
            
            for m in matches:
                # ID'sini senin sistemine uygun hale getir
                fixed_p = re.sub(r'channel="[^"]+"', f'channel="{target_id}"', m)
                rich_programmes += fixed_p + "\n"
            
            # Ana dosyadan bu kanalların (varsa) eski/boş verilerini temizle
            xml_main = re.sub(rf'<programme[^>]+channel="{re.escape(target_id)}".*?</programme>', '', xml_main, flags=re.DOTALL)

        print("3. Veriler birleştiriliyor...")
        
        # Zengin programları ana dosyaya enjekte et
        xml_final = xml_main.replace('</tv>', rich_programmes + "\n</tv>")

        # Karakter setini garantilemek için mühürle
        with open("epg.xml", "w", encoding="utf-8-sig") as f:
            f.write(xml_final)
            
        print("--- BAŞARILI: Hibrit sistem aktif! ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
