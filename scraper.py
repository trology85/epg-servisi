import requests
import gzip
import io
import re
import xml.etree.ElementTree as ET

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    rich_url = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Kaynaklar indiriliyor...")
        # Ana Kaynak (Saatleri Doğru Olan)
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_main = f.read().decode('utf-8')
        
        # Zengin Kaynak (Sadece Açıklama İçin)
        resp_rich = requests.get(rich_url, timeout=60)
        resp_rich.encoding = 'utf-8'
        xml_rich = resp_rich.text

        # FOX -> NOW dönüşümü
        xml_main = xml_main.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"').replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        print("2. Açıklama eşleştirme motoru çalışıyor...")
        
        # Zengin kaynaktaki açıklamaları bir sözlüğe (dictionary) alalım
        # Anahtar: "Program Adı", Değer: "Açıklama"
        descriptions = {}
        rich_titles = re.findall(r'<title lang="tr">(.*?)</title>.*?<desc lang="tr">(.*?)</desc>', xml_rich, flags=re.DOTALL)
        for title, desc in rich_titles:
            descriptions[title.strip().lower()] = desc.strip()

        # Ana dosyadaki her programı kontrol et ve eğer açıklaması yoksa/kısaysa zengin kaynaktan ekle
        def add_desc(match):
            prog_xml = match.group(0)
            # Eğer programın zaten bir açıklaması varsa dokunma (veya değiştir)
            if '<desc' in prog_xml:
                return prog_xml
            
            title_match = re.search(r'<title lang="tr">(.*?)</title>', prog_xml)
            if title_match:
                title = title_match.group(1).strip().lower()
                if title in descriptions:
                    new_desc = f'\n    <desc lang="tr">{descriptions[title]}</desc>'
                    return prog_xml.replace('</title>', f'</title>{new_desc}')
            return prog_xml

        # Tüm program blokları üzerinde bu işlemi yap
        final_xml = re.sub(r'<programme.*?</programme>', add_desc, xml_main, flags=re.DOTALL)

        # Karakter ve CNBC-E/DMAX düzeltmeleri
        final_xml = final_xml.replace('id="CNBC-e"', 'id="CNBC-E"').replace('channel="CNBC-e"', 'channel="CNBC-E"')
        
        with open("epg.xml", "w", encoding="utf-8-sig") as f:
            f.write(final_xml)
            
        print("--- BAŞARILI: Saatler korundu, açıklamalar transfer edildi! ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
