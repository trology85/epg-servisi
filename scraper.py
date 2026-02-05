import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url, channel_type):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []

        if "cnbce" in url:
            # CNBC-e özel kazıma mantığı
            # Sitedeki program kutularını hedefliyoruz
            items = soup.select('.program-card') or soup.select('.list-item') or soup.find_all('div', class_=re.compile(r'program'))
            for item in items:
                time_el = item.select_one('.time') or item.select_one('.hour')
                title_el = item.select_one('.title') or item.select_one('h3')
                desc_el = item.select_one('.description') or item.select_one('p')
                
                if time_el and title_el:
                    programs.append({
                        'time': time_el.get_text(strip=True).replace('.', ':'),
                        'title': title_el.get_text(strip=True),
                        'desc': desc_el.get_text(strip=True) if desc_el else "CNBC-e yayın akışı."
                    })
        else:
            # DMAX ve Genel kazıma
            items = soup.find_all(class_=re.compile(r'(broadcast-item|stream-item|timeline-item)'))
            for item in items:
                time_el = item.select_one('.time') or item.select_one('.hour')
                title_el = item.select_one('.title') or item.select_one('h3')
                if time_el and title_el:
                    time_str = time_el.get_text(strip=True).replace('.', ':')
                    if re.match(r'^\d{2}:\d{2}$', time_str):
                        programs.append({
                            'time': time_str,
                            'title': title_el.get_text(strip=True),
                            'desc': "Program detayı DMAX ekranlarında."
                        })
        return programs
    except Exception as e:
        print(f"Hata ({url}): {e}")
        return []

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    try:
        print("1. Ana EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TEMİZLİK VE KANAL TANIMLARI ---
        # CNBC-E için ID: "CNBC-E" (Listenle eşleşmesi için)
        target_ids = ["DMAX.HD.tr", "CNBC-E"]
        
        for tid in target_ids:
            # Mevcut programları temizle
            xml_content = re.sub(f'<programme[^>]+channel="{re.escape(tid)}".*?</programme>', '', xml_content, flags=re.DOTALL)
            # Kanal tanımı yoksa ekle (</tv> etiketinden önce)
            if f'id="{tid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{tid}">\n    <display-name lang="tr">{tid}</display-name>\n  </channel>\n</tv>')

        print("2. Veriler web'den çekiliyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi", "dmax")
        cnbce_list = get_real_web_data("https://www.cnbce.com/yayin-akisi", "cnbce")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Verilerini Yaz
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="DMAX.HD.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # CNBC-E Verilerini Yaz
        for p in cnbce_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="CNBC-E">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # Boş açıklamaları doldur (Diğer kanallar için)
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        # Tüm yeni verileri XML'e enjekte et
        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"--- BAŞARILI --- DMAX: {len(dmax_list)} | CNBC-e: {len(cnbce_list)}")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
