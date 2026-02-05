import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_data_universal(url, channel_name):
    """Farklı kanal yapılarına göre veri çeker."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        # CNBC-E ÖZEL: Eğer kendi sitesi kapalıysa alternatif bir akış sitesinden deneyelim
        if channel_name == "CNBC-E":
            # Alternatif olarak tvyayinakisi.com veya benzeri bir aggregator deniyoruz
            test_url = "https://www.tvyayinakisi.com/cnbc-e-yayin-akisi/"
            r = requests.get(test_url, headers=headers, timeout=20)
        else:
            r = requests.get(url, headers=headers, timeout=20)
            
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []

        # Tüm sayfadaki Saat - Program eşleşmelerini ara (En garantici yöntem)
        # Regex: 00:00 ile 23:59 arası saatleri ve yanındaki metni bulur
        text_content = soup.get_text(" | ", strip=True)
        matches = re.findall(r'(\d{2}[:\.]\d{2})\s*\|\s*([^|]{3,60})', text_content)

        if not matches:
            # Alternatif regex (Saat ve metin yan yanaysa)
            matches = re.findall(r'(\d{2}[:\.]\d{2})\s+([A-ZÇĞİÖŞÜ].{3,50})', text_content)

        for m in matches:
            time_str = m[0].replace('.', ':')
            title_str = m[1].strip()
            # Gereksiz kelimeleri filtrele
            if len(title_str) > 3 and not any(x in title_str for x in ["Giriş", "Üye", "Daha Fazla", "Yayın Akışı"]):
                results.append({'time': time_str, 'title': title_str})

        return results
    except:
        return []

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    try:
        print("1. Kaynak EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Web verileri kazınıyor...")
        # DMAX için orijinal sitesi hala 9 veriyor, CNBC-E için alternatif deniyoruz
        dmax_data = get_data_universal("https://www.dmax.com.tr/yayin-akisi", "DMAX")
        cnbce_data = get_data_universal("https://www.cnbce.com/yayin-akisi", "CNBC-E")

        print(f"> DMAX Bulunan: {len(dmax_data)}")
        print(f"> CNBC-e Bulunan: {len(cnbce_data)}")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # Kanalları XML'e ekle
        for cid, data_list in [("DMAX.HD.tr", dmax_data), ("CNBC-E", cnbce_data)]:
            # Kanal tanımı yoksa ekle
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')
            
            # Programları ekle
            for p in data_list:
                clean_time = p['time'].replace(':', '')[:4]
                start = f"{today}{clean_time}00 +0300"
                new_entries += f'  <programme start="{start}" channel="{cid}">\n'
                new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
                new_entries += f'    <desc lang="tr">{p["title"]} - {cid} Yayın Akışı</desc>\n'
                new_entries += f'  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
