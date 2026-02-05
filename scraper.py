import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_cnbce_final_attempt():
    """CNBC-e için Mynet TV Rehberi üzerinden veri çeker."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    # Alternatif Kaynak 2: Mynet TV Rehberi
    url = "https://tvrehberi.mynet.com/cnbc-e-yayin-akisi/"
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        programs = []
        
        # Mynet yapısı: .tv-guide-list içindeki öğeler
        items = soup.select('.tv-guide-list-item') or soup.find_all('li', class_=re.compile(r'item'))
        for item in items:
            time_el = item.select_one('.time') or item.find(string=re.compile(r'^\d{2}:\d{2}$'))
            title_el = item.select_one('.title') or item.find(['h3', 'h4', 'span'])
            
            if time_el and title_el:
                programs.append({
                    'time': time_el.get_text(strip=True),
                    'title': title_el.get_text(strip=True)
                })
        
        # Eğer yukarıdaki çalışmazsa Regex ile tüm sayfayı tara (CNBC-E için son çare)
        if not programs:
            text = soup.get_text(" | ")
            matches = re.findall(r'(\d{2}:\d{2})\s*\|\s*([^|]{3,50})', text)
            for m in matches:
                if not any(x in m[1] for x in ["Giriş", "Üye", "Yayın"]):
                    programs.append({'time': m[0], 'title': m[1].strip()})
                    
        return programs
    except:
        return []

def get_dmax_data():
    """DMAX için çalışan mevcut yapıyı korur."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://www.dmax.com.tr/yayin-akisi", headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        text_content = soup.get_text(" | ", strip=True)
        matches = re.findall(r'(\d{2}[:\.]\d{2})\s*\|\s*([^|]{3,60})', text_content)
        return [{'time': m[0].replace('.', ':'), 'title': m[1].strip()} for m in matches]
    except:
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

        print("2. Veriler toplanıyor...")
        dmax_list = get_dmax_data()
        cnbce_list = get_cnbce_final_attempt()

        print(f"> DMAX: {len(dmax_list)} | CNBC-e: {len(cnbce_list)}")

        new_entries = ""
        today = datetime.now().strftime("%Y%m%d")

        for cid, data in [("DMAX.HD.tr", dmax_list), ("CNBC-E", cnbce_list)]:
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')
            
            for p in data:
                start = f"{today}{p['time'].replace(':', '')}00 +0300"
                new_entries += f'  <programme start="{start}" channel="{cid}">\n'
                new_entries += f'    <title lang="tr">{p["title"]}</title>\n'
                new_entries += f'    <desc lang="tr">{cid} Program Akışı</desc>\n'
                new_entries += f'  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_entries + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
