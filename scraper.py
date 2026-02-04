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

        # FOX -> NOW Değişimi (Standart)
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # --- TRT 2 KANALI TANIMI (UYGULAMA TANISIN DİYE) ---
        # Hem 'TRT 2' hem 'TRT2.tr' ID'lerini tanıyacak şekilde çoklu tanım ekliyoruz
        trt2_def = '  <channel id="TRT 2">\n    <display-name lang="tr">TRT 2</display-name>\n    <display-name lang="tr">TRT 2 HD</display-name>\n  </channel>\n'
        trt2_def += '  <channel id="TRT2.tr">\n    <display-name lang="tr">TRT 2</display-name>\n  </channel>\n'
        xml_content = xml_content.replace('</tv>', trt2_def + '</tv>')

        # --- ESKİ PROGRAMLARI TEMİZLE ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="TRT2\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        xml_content = re.sub(r'<programme[^>]+channel="TRT 2".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Web'den veriler alınıyor...")
        dmax_data = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_data = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Ekleme
        for p in dmax_data:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_entries += f'  <programme start="{start}" channel="DMAX.HD.tr">\n'
            new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
            new_entries += f'    <desc lang="tr">{p["desc"] if p["desc"] else "DMAX Program Detayı"}</desc>\n'
            new_entries += f'  </programme>\n'

        # TRT 2 Ekleme (Her iki olası ID için de ekleyelim ki biri mutlaka tutsun)
        for p in trt2_data:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            # Hem 'TRT 2' ID'si için ekle
            new_entries += f'  <programme start="{start}" channel="TRT 2">\n'
            new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
            new_entries += f'    <desc lang="tr">{p["desc"] if p["desc"] else "TRT 2 Program Detayı"}</desc>\n'
            new_entries += f'  </programme>\n'
            # Hem 'TRT2.tr' ID'si için ekle (Garanti olsun)
            new_entries += f'  <programme start="{start}" channel="TRT2.tr">\n'
            new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
            new_entries += f'    <desc lang="tr">{p["desc"] if p["desc"] else "TRT 2 Program Detayı"}</desc>\n'
            new_entries += f'  </programme>\n'

        print("3. Boş açıklamalar dolduruluyor...")
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
