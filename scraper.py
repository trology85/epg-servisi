import requests
import gzip
import io
import re
from datetime import datetime
import xml.etree.ElementTree as ET

def get_programmes_from_external_xml(source_url, target_channel_id):
    """Büyük bir EPG dosyasını indirir ve içinden belirli bir kanalı ayıklar."""
    print(f"   - {target_channel_id} için {source_url} taranıyor...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(source_url, timeout=40)
        # Eğer dosya sıkıştırılmışsa (.gz) aç
        if source_url.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
                content = f.read().decode('utf-8')
        else:
            content = resp.text
        
        # Regex ile sadece bu kanala ait programları söküp alalım
        # Bu yöntem XML parse etmekten çok daha hızlıdır
        pattern = f'<programme[^>]+channel="{re.escape(target_channel_id)}".*?</programme>'
        matches = re.findall(pattern, content, flags=re.DOTALL)
        return matches
    except Exception as e:
        print(f"   ! Kaynak hatası: {e}")
        return []

def update_epg():
    # Ana EPG dosyamız (Senin kullandığın)
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    
    # CNBC-e ve DMAX'i bulabileceğimiz alternatif dev havuzlar
    alt_sources = [
        "https://iptv-org.github.io/epg/guides/tr/beintv.com.epg.xml",
        "https://raw.githubusercontent.com/LITUATUI/GUIA-TV/master/guia.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
    ]

    try:
        print("1. Ana EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK ---
        # Mevcut (boş veya hatalı) DMAX ve CNBC-e verilerini siliyoruz
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Alternatif havuzlardan veri toplanıyor...")
        
        # CNBC-E ARAYIŞI
        cnbce_programmes = []
        for source in alt_sources:
            # CNBC-e havuzlarda farklı ID'lerle olabilir, hepsini deneyelim
            for possible_id in ["CNBC-e.tr", "CNBC-E", "CNBCE.tr"]:
                found = get_programmes_from_external_xml(source, possible_id)
                if found:
                    # Bulunanları bizim kendi ID'mizle ("CNBC-E") değiştirerek ekle
                    for p in found:
                        p_fixed = re.sub(r'channel="[^"]+"', 'channel="CNBC-E"', p)
                        cnbce_programmes.append(p_fixed)
                    break
            if cnbce_programmes: break

        # DMAX ARAYIŞI (Zaten çalışıyordu ama daha sağlam olsun diye havuzdan da bakıyoruz)
        dmax_programmes = get_programmes_from_external_xml(main_url, "DMAX.HD.tr")

        print(f"> Sonuç: DMAX için {len(dmax_programmes)}, CNBC-e için {len(cnbce_programmes)} veri bulundu.")

        # --- BİRLEŞTİRME ---
        # Kanal tanımlarını garantiye al
        for cid in ["DMAX.HD.tr", "CNBC-E"]:
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')

        # Bulunan programları ekle
        all_new = "\n".join(dmax_programmes) + "\n" + "\n".join(cnbce_programmes)
        xml_content = xml_content.replace('</tv>', all_new + "\n</tv>")

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
