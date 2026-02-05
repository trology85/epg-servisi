import requests
import gzip
import io
import re
from datetime import datetime

def get_channel_from_xml(url, target_id, my_id):
    """Belirli bir XML linkinden belirli bir kanalı çeker ve ID'sini günceller."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        print(f"   - {target_id} aranıyor: {url}")
        resp = requests.get(url, headers=headers, timeout=30)
        # Dosya sıkıştırılmış mı kontrol et
        if url.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
                content = f.read().decode('utf-8')
        else:
            content = resp.text # Senin verdiğin link düz XML

        # Regex: Bu kanala ait tüm <programme> bloklarını bul
        # Not: Kaynakta kanal id'si tam olarak nasılsa onu arıyoruz
        pattern = f'<programme[^>]+channel="{re.escape(target_id)}".*?</programme>'
        matches = re.findall(pattern, content, flags=re.DOTALL)
        
        # Bulunan programlardaki kanal ismini senin istediğin (my_id) ile değiştir
        fixed_matches = []
        for p in matches:
            fixed_p = re.sub(r'channel="[^"]+"', f'channel="{my_id}"', p)
            fixed_matches.append(fixed_p)
            
        return fixed_matches
    except Exception as e:
        print(f"   ! Hata: {e}")
        return []

def update_epg():
    # Senin verdiğin yeni ve sağlam kaynak
    gold_source = "https://streams.uzunmuhalefet.com/epg/tr.xml"
    # Orijinal ana kaynak (Diğer kanallar için)
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"

    try:
        print("1. Ana EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Yeni kaynaktan veriler çekiliyor...")
        
        # CNBC-e Çekme (Kaynaktaki ID'si: "CNBC-e", Senin istediğin: "CNBC-E")
        cnbce_data = get_channel_from_xml(gold_source, "CNBC-e", "CNBC-E")
        
        # DMAX Çekme (Kaynaktaki ID'si: "DMAX", senin sistemindekiyle eşleştiriyoruz)
        dmax_data = get_channel_from_xml(gold_source, "DMAX", "DMAX.HD.tr")

        print(f"> SONUÇ: DMAX: {len(dmax_data)} | CNBC-e: {len(cnbce_data)}")

        # --- BİRLEŞTİRME ---
        # Kanal tanımlarını en sona ekle
        for cid in ["DMAX.HD.tr", "CNBC-E"]:
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')

        # Programları ekle
        all_new = "\n".join(dmax_data) + "\n" + "\n".join(cnbce_data)
        xml_content = xml_content.replace('</tv>', all_new + "\n</tv>")

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Sistem Hatası: {e}")

if __name__ == "__main__":
    update_epg()
