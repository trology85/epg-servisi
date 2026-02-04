import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []
        # Hem DMAX hem TRT için ortak arama
        items = soup.find_all(class_=re.compile(r'(broadcast-item|stream-item|timeline-item)'))
        for item in items:
            time_el = item.select_one('.time') or item.select_one('.hour')
            title_el = item.select_one('.title') or item.select_one('h3')
            desc_el = item.select_one('.description') or item.select_one('p')
            if time_el and title_el:
                time_str = time_el.get_text(strip=True)
                if re.match(r'^\d{2}[:\.]\d{2}$', time_str):
                    programs.append({
                        'time': time_str.replace('.', ':'),
                        'title': title_el.get_text(strip=True),
                        'desc': desc_el.get_text(strip=True) if desc_el else "Program detayı."
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

        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- SADECE DMAX TEMİZLİĞİ (TRT'LERE DOKUNMUYORUZ) ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Veriler kazınıyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_list = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Ekleme (Büyük harf orijinal ID)
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="DMAX.HD.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # TRT 2 Ekleme (Sadece dosyanın en sonuna ekliyoruz, mevcutları silmiyoruz)
        if trt2_list:
            # TRT 2 Kimlik Tanımı
            new_entries += '  <channel id="TRT2.tr">\n    <display-name lang="tr">TRT 2</display-name>\n  </channel>\n'
            for p in trt2_list:
                start = f"{today}{p['time'].replace(':', '')}00 +0300"
                new_entries += f'  <programme start="{start}" channel="TRT2.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # Boş açıklamaları doldur (Genel yama)
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        # Her şeyi en sona ekle
        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print(f"--- BAŞARILI --- DMAX: {len(dmax_list)} | TRT 2: {len(trt2_list)}")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
