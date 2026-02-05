import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_data_v3(url):
    """Gelişmiş session ve regex ile veri çekme."""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com"
    }
    
    try:
        response = session.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        # Eğer site boş dönerse veya hata verirse
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        # 1. YÖNTEM: HTML içindeki tüm metinleri al ve Regex ile Saat-Başlık ikilisi ara
        # Bu yöntem class isimleri değişse bile çalışır.
        # Genelde "12:00 Program Adı" veya "12:00 | Program Adı" şeklindedir.
        text_content = soup.get_text(" ", strip=True)
        # Saat (HH:MM) ve sonrasındaki metni yakalayan regex
        matches = re.findall(r'(\d{2}[:\.]\d{2})\s*[-|]?\s*([A-ZÇĞİÖŞÜ0-9][^:]{3,60})', text_content)

        for m in matches:
            time_str = m[0].replace('.', ':')
            title_str = m[1].strip()
            # Gereksiz kısa veya sistem metinlerini ele (Örn: "DMAX Yayın")
            if len(title_str) > 3 and not any(x in title_str for x in ["Giriş Yap", "Üye Ol", "Çerez"]):
                results.append({'time': time_str, 'title': title_str})

        # 2. YÖNTEM: Eğer regex az sonuç verdiyse standart kazımaya dön (DMAX için)
        if len(results) < 5:
            for item in soup.select('.broadcast-item, .program-card, .list-item'):
                t = item.select_one('.time, .hour')
                n = item.select_one('.title, h3')
                if t and n:
                    results.append({'time': t.text.strip(), 'title': n.text.strip()})

        return results
    except Exception as e:
        print(f"Hata oluştu ({url}): {e}")
        return []

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    try:
        print("1. Kaynak EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        # Kanal Tanımları
        for cid in ["DMAX.HD.tr", "CNBC-E"]:
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')

        print("2. Web verileri kazınıyor...")
        dmax_data = get_data_v3("https://www.dmax.com.tr/yayin-akisi")
        cnbce_data = get_data_v3("https://www.cnbce.com/yayin-akisi")

        print(f"> DMAX Bulunan: {len(dmax_data)}")
        print(f"> CNBC-e Bulunan: {len(cnbce_data)}")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # Verileri XML'e İşle
        for cid, data_list in [("DMAX.HD.tr", dmax_data), ("CNBC-E", cnbce_data)]:
            for p in data_list:
                clean_time = p['time'].replace(':', '')[:4] # HHMM formatı
                start = f"{today}{clean_time}00 +0300"
                new_entries += f'  <programme start="{start}" channel="{cid}">\n'
                new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
                new_entries += f'    <desc lang="tr">{cid} Program Akışı</desc>\n'
                new_entries += f'  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Genel Hata: {e}")

if __name__ == "__main__":
    update_epg()
