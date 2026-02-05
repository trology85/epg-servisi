import requests
import gzip
import io
import re
from datetime import datetime

def update_epg():
    # Kaynaklar
    gold_source = "https://streams.uzunmuhalefet.com/epg/tr.xml"
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"

    try:
        print("1. Ana EPG (TR1) indiriliyor...")
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_main = f.read().decode('utf-8')

        print("2. Yeni kaynak (tr.xml) indiriliyor...")
        resp_gold = requests.get(gold_source, timeout=60)
        xml_gold = resp_gold.text

        # --- FOX -> NOW DEĞİŞİMİ (Zaten vardı) ---
        xml_main = xml_main.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_main = xml_main.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- CNBC-E, DMAX ve TRT 2 DEĞİŞİMLERİ ---
        # tr.xml içindeki kanal isimlerini senin sistemindekilerle eşleştiriyoruz
        
        # 1. CNBC-e Değişimi
        xml_gold = xml_gold.replace('channel="CNBC-e"', 'channel="CNBC-E"')
        xml_gold = xml_gold.replace('id="CNBC-e"', 'id="CNBC-E"')
        
        # 2. DMAX Değişimi
        xml_gold = xml_gold.replace('channel="DMAX"', 'channel="DMAX.HD.tr"')
        xml_gold = xml_gold.replace('id="DMAX"', 'id="DMAX.HD.tr"')

        # 3. TRT 2 Değişimi
        # Kaynakta "TRT 2" olarak geçiyor, senin ID'lerinle eşleştiriyoruz
        xml_gold = xml_gold.replace('channel="TRT 2"', 'channel="TRT2.tr"')
        xml_gold = xml_gold.replace('id="TRT 2"', 'id="TRT2.tr"')

        print("3. Veriler ayıklanıyor ve birleştiriliyor...")
        
        # tr.xml'den sadece program bloklarını çekelim
        # Bu sefer regex'i çok daha geniş tutuyoruz ki her şeyi yakalasın
        new_programmes = re.findall(r'(<programme.*?</programme>)', xml_gold, flags=re.DOTALL)
        
        # Sadece bizim istediğimiz kanallara ait olanları filtrele
        filtered_programmes = []
        target_ids = ["CNBC-E", "DMAX.HD.tr", "TRT2.tr"]
        
        for p in new_programmes:
            if any(f'channel="{tid}"' in p for tid in target_ids):
                filtered_programmes.append(p)

        # --- ANA DOSYADAN ESKİLERİ TEMİZLE ---
        for tid in target_ids:
            xml_main = re.sub(rf'<programme[^>]+channel="{re.escape(tid)}".*?</programme>', '', xml_main, flags=re.DOTALL)

        # --- BİRLEŞTİR ---
        combined_data = "\n".join(filtered_programmes)
        xml_final = xml_main.replace('</tv>', combined_data + '\n</tv>')

        # Kanal tanımlarını (Channel Tags) kontrol et/ekle
        for tid in target_ids:
            if f'id="{tid}"' not in xml_final:
                xml_final = xml_final.replace('</tv>', f'  <channel id="{tid}">\n    <display-name lang="tr">{tid}</display-name>\n  </channel>\n</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_final)
            
        print(f"--- BAŞARILI ---")
        print(f"Toplam eklenen program sayısı: {len(filtered_programmes)}")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
