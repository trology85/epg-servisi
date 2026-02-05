import requests
import gzip
import io
import re
from datetime import datetime

def get_channel_from_xml(url, target_id_pattern, my_id):
    """Gelişmiş arama ile XML içinden kanalı söker alır."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        print(f"   - {target_id_pattern} aranıyor...")
        # Stream=True yaparak büyük dosyaları daha güvenli indiriyoruz
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        content = resp.text

        # REGEX: Büyük/Küçük harf duyarsız ve daha esnek bir arama
        # channel="CNBC-e" veya channel="cnbce" gibi varyasyonları yakalar
        pattern = rf'<programme[^>]+channel="(?i:{target_id_pattern})".*?</programme>'
        matches = re.findall(pattern, content, flags=re.DOTALL)
        
        fixed_matches = []
        for p in matches:
            # Bulunan kanal ismini senin istediğin standart ID ile değiştir
            fixed_p = re.sub(r'channel="[^"]+"', f'channel="{my_id}"', p)
            fixed_matches.append(fixed_p)
            
        return fixed_matches
    except Exception as e:
        print(f"   ! Arama hatası: {e}")
        return []

def update_epg():
    gold_source = "https://streams.uzunmuhalefet.com/epg/tr.xml"
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"

    try:
        print("1. Kaynak dosyalar yükleniyor (Bu işlem 1-2 dakika sürebilir)...")
        
        # CNBC-E için (Kaynakta CNBC-e olarak geçiyor olabilir)
        cnbce_data = get_channel_from_xml(gold_source, "CNBC-e", "CNBC-E")
        
        # DMAX için (Kaynakta DMAX veya Dmax olabilir)
        dmax_data = get_channel_from_xml(gold_source, "DMAX", "DMAX.HD.tr")

        if len(cnbce_data) == 0:
            print("   ! CNBC-e bulunamadı, alternatif isim 'cnbce' deneniyor...")
            cnbce_data = get_channel_from_xml(gold_source, "cnbce", "CNBC-E")

        print(f"> SONUÇ: DMAX: {len(dmax_data)} | CNBC-e: {len(cnbce_data)}")

        # --- XML BİRLEŞTİRME ---
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_content = f.read().decode('utf-8')

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"').replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # Eski verileri temizle
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        # Kanal Tanımları
        for cid in ["DMAX.HD.tr", "CNBC-E"]:
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')

        # Yeni programları ekle
        all_new_data = "\n".join(dmax_data) + "\n" + "\n".join(cnbce_data)
        xml_content = xml_content.replace('</tv>', all_new_data + "\n</tv>")

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Sistem Hatası: {e}")

if __name__ == "__main__":
    update_epg()
