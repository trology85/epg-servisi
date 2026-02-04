import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []
        items = soup.find_all(class_=re.compile(r'(broadcast-item|stream-item|timeline-item|card)'))
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

        # --- DİKKATLİ TEMİZLİK (Sadece Hedef Kanallar) ---
        # Regex'i 'channel="TRT2.tr"' gibi tam eşleşme arayacak şekilde güncelledim.
        # Böylece TRT 1 veya TRT Haber'e dokunmayacak.
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="TRT2\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="TRT 2".*?</programme>', '', xml_content, flags=re.DOTALL)

        # TRT 2 Kanal Tanımı (Eğer yoksa)
        if 'id="TRT 2"' not in xml_content:
            xml_content = xml_content.replace('</tv>', '  <channel id="TRT 2">\n    <display-name lang="tr">TRT 2</display-name>\n  </channel>\n</tv>')

        print("2. Veriler web'den çekiliyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_list = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_programs = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Verileri
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_programs += f'  <programme start="{start}" channel="DMAX.HD.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # TRT 2 Verileri (Hem 'TRT 2' hem 'TRT2.tr' ID'sine basıyoruz ki garanti olsun)
        for p in trt2_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            for cid in ["TRT 2", "TRT2.tr"]:
                new_programs += f'  <programme start="{start}" channel="{cid}">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # Boş açıklamaları doldur (Diğer kanallar için)
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        xml_content = xml_content.replace('</tv>', new_programs + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"Bitti! TRT 2 için {len(trt2_list)} program eklendi.")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
