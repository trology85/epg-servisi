import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_cnbce_data():
    """CNBC-e verilerini API üzerinden çeker."""
    url = "https://www.cnbce.com/api/yayin-akisi" # CNBC-e'nin veri sağladığı uç nokta
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cnbce.com/"}
    try:
        # Not: Eğer bu API direkt çalışmazsa, web sayfasını farklı bir teknikle kazıyacağız
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            programs = []
            # API'den gelen JSON yapısını parse ediyoruz (Varsayımsal yapıya göre)
            for item in data.get('data', []) or data.get('items', []):
                programs.append({
                    'time': item.get('time', '').replace('.', ':'),
                    'title': item.get('title', 'Program'),
                    'desc': item.get('description', 'CNBC-e Yayın Akışı')
                })
            return programs
    except:
        pass
    
    # API hata verirse alternatif "Derin Kazıma" (Farklı Class yapıları ile)
    try:
        r = requests.get("https://www.cnbce.com/yayin-akisi", headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        alt_programs = []
        # CNBC-e'nin şu anki güncel HTML yapısı: .stream-item veya .program-card
        for item in soup.select('.stream-item, .program-list-item, [class*="program"]'):
            time_el = item.select_one('.time, .hour, .date')
            title_el = item.select_one('.title, .name, h3, h4')
            if time_el and title_el:
                alt_programs.append({
                    'time': time_el.get_text(strip=True).replace('.', ':'),
                    'title': title_el.get_text(strip=True),
                    'desc': "Yayın detayı CNBC-e web sitesindedir."
                })
        return alt_programs
    except:
        return []

def get_dmax_data():
    """DMAX verilerini kazır."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://www.dmax.com.tr/yayin-akisi", headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []
        for item in soup.select('.broadcast-item'):
            time_el = item.select_one('.time')
            title_el = item.select_one('.title')
            if time_el and title_el:
                programs.append({
                    'time': time_el.text.strip().replace('.', ':'),
                    'title': title_el.text.strip()
                })
        return programs
    except:
        return []

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    try:
        print("1. Ana EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="CNBC-E".*?</programme>', '', xml_content, flags=re.DOTALL)

        # Kanal Tanımı Ekle (CNBC-E)
        if 'id="CNBC-E"' not in xml_content:
            xml_content = xml_content.replace('</tv>', '  <channel id="CNBC-E">\n    <display-name lang="tr">CNBC-E</display-name>\n  </channel>\n</tv>')

        print("2. Veriler toplanıyor...")
        dmax_list = get_dmax_data()
        cnbce_list = get_cnbce_data()

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="DMAX.HD.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">DMAX Yayın Akışı</desc>\n  </programme>\n'

        for p in cnbce_list:
            # CNBC-e bazen saatte sadece '20:00' değil, 'Bugün 20:00' gibi şeyler yazabilir.
            # Sadece saat kısmını çekelim:
            match = re.search(r'(\d{2}:\d{2})', p['time'])
            clean_time = match.group(1) if match else "00:00"
            start = f"{today}{clean_time.replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="CNBC-E">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p.get("desc", "CNBC-e Programı")}</desc>\n  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"--- SONUÇ --- DMAX: {len(dmax_list)} | CNBC-e: {len(cnbce_list)}")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
