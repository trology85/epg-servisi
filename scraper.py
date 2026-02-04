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
        items = soup.select('.broadcast-item') or soup.select('.stream-item')
        for item in items:
            time_el = item.select_one('.time')
            title_el = item.select_one('.title') or item.select_one('h3')
            desc_el = item.select_one('.description') or item.select_one('p')
            if time_el and title_el:
                programs.append({
                    'time': time_el.text.strip(),
                    'title': title_el.text.strip(),
                    'desc': desc_el.text.strip() if desc_el else ""
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

        # --- TÜM TRT 2 VARYASYONLARINI SİSTEME TANIT ---
        # Uygulama neyi ararsa onu bulsun diye ID listesini genişletiyoruz
        possible_ids = ["TRT 2", "TRT2.tr", "TRT 2 HD", "trt 2", "trt2.tr"]
        trt2_defs = ""
        for pid in possible_ids:
            trt2_defs += f'  <channel id="{pid}">\n    <display-name lang="tr">{pid}</display-name>\n    <display-name lang="tr">TRT 2 HD</display-name>\n  </channel>\n'
        
        xml_content = xml_content.replace('</tv>', trt2_defs + '</tv>')

        # --- TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        for pid in possible_ids:
            clean_pattern = f'<programme[^>]+channel="{pid}".*?</programme>'
            xml_content = re.sub(clean_pattern, '', xml_content, flags=re.DOTALL)

        print("2. Veriler çekiliyor...")
        dmax_data = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_data = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Ekleme
        for p in dmax_data:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="DMAX.HD.tr">\n'
            new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
            new_entries += f'    <desc lang="tr">{p["desc"] if p["desc"] else "Program detayı."}</desc>\n'
            new_entries += f'  </programme>\n'

        # TRT 2 Ekleme (TÜM ID'LERE AYNI VERİYİ BASIYORUZ)
        for p in trt2_data:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            for pid in possible_ids:
                new_entries += f'  <programme start="{start}" channel="{pid}">\n'
                new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
                new_entries += f'    <desc lang="tr">{p["desc"] if p["desc"] else "Program detayı."}</desc>\n'
                new_entries += f'  </programme>\n'

        print("3. Yamalar yapılıyor...")
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları ve program özeti.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI! ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
