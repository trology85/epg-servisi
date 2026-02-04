import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    """Web sitesinden programları çeker."""
    headers = {"User-Agent": "Mozilla/5.0"}
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

        # --- TEMİZLİK ---
        # Mevcut DMAX verilerini siliyoruz (ID'ye dokunmadan programları temizliyoruz)
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Veriler kazınıyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_list = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_xml_part = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX'i orijinal ID'si ile geri ekliyoruz
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_xml_part += f'  <programme start="{start}" channel="DMAX.HD.tr">\n'
            new_xml_part += f'    <title lang="tr">{p["title"]}</title>\n'
            new_xml_part += f'    <desc lang="tr">{p["desc"] if p["desc"] else "Program detayı bulunmuyor."}</desc>\n'
            new_xml_part += f'  </programme>\n'

        # TRT 2'yi ekliyoruz (Eğer TRT 2 kanalı tanımlı değilse en alta ekliyoruz)
        if 'id="TRT2.tr"' not in xml_content:
            new_xml_part += '  <channel id="TRT2.tr">\n    <display-name lang="tr">TRT 2</display-name>\n    <display-name lang="tr">TRT 2 HD</display-name>\n  </channel>\n'
        
        for p in trt2_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_xml_part += f'  <programme start="{start}" channel="TRT2.tr">\n'
            new_xml_part += f'    <title lang="tr">{p["title"]}</title>\n'
            new_xml_part += f'    <desc lang="tr">{p["desc"] if p["desc"] else "Program detayı bulunmuyor."}</desc>\n'
            new_xml_part += f'  </programme>\n'

        print("3. Boş açıklamalar dolduruluyor...")
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları ve program özeti.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        # Hepsini XML'e enjekte et
        xml_content = xml_content.replace('</tv>', new_xml_part + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- BAŞARIYLA TAMAMLANDI ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
