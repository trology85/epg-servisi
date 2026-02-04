import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []
        
        # TRT ve DMAX için tüm olası class isimlerini tarıyoruz
        items = soup.find_all(class_=re.compile(r'(broadcast-item|stream-item|timeline-item|card)'))
        
        for item in items:
            # Zamanı bul (Farklı class isimlerine bakıyoruz)
            time_el = item.select_one('.time') or item.select_one('.hour') or item.select_one('.date')
            # Başlığı bul
            title_el = item.select_one('.title') or item.select_one('h3') or item.select_one('.name')
            # Açıklamayı bul
            desc_el = item.select_one('.description') or item.select_one('p') or item.select_one('.short-description')
            
            if time_el and title_el:
                time_str = time_el.get_text(strip=True)
                # Sadece HH:MM formatındaki (00:00 gibi) verileri al
                if re.match(r'^\d{2}[:\.]\d{2}$', time_str):
                    programs.append({
                        'time': time_str.replace('.', ':'),
                        'title': title_el.get_text(strip=True),
                        'desc': desc_el.get_text(strip=True) if desc_el else "Program detayı bulunmuyor."
                    })
        
        # Eğer yukarıdaki yöntem boş dönerse (Alternatif TRT tablosu)
        if not programs:
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    time_str = cols[0].get_text(strip=True)
                    if re.match(r'^\d{2}[:\.]\d{2}$', time_str):
                        programs.append({
                            'time': time_str.replace('.', ':'),
                            'title': cols[1].get_text(strip=True),
                            'desc': cols[2].get_text(strip=True) if len(cols) > 2 else "Yayın akışı."
                        })
        
        return programs
    except Exception as e:
        print(f"Kazıma hatası ({url}): {e}")
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

        # --- KANAL TANIMLARI ---
        # Uygulamanın yakalayabileceği en güçlü ID'leri ekliyoruz
        custom_ids = ["TRT 2", "TRT2.tr", "TRT 2 HD"]
        trt_defs = ""
        for cid in custom_ids:
            trt_defs += f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n'
        xml_content = xml_content.replace('</tv>', trt_defs + '</tv>')

        # Temizlik
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        for cid in custom_ids:
            xml_content = re.sub(f'<programme[^>]+channel="{cid}".*?</programme>', '', xml_content, flags=re.DOTALL)

        print("2. Veriler web'den çekiliyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_list = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_programs = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Verileri (DMAX.HD.tr için)
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_programs += f'  <programme start="{start}" channel="DMAX.HD.tr">\n'
            new_programs += f'    <title lang="tr">{p["title"]}</title>\n'
            new_programs += f'    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # TRT 2 Verileri (Belirlediğimiz 3 ID için de basıyoruz)
        for p in trt2_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            for cid in custom_ids:
                new_programs += f'  <programme start="{start}" channel="{cid}">\n'
                new_programs += f'    <title lang="tr">{p["title"]}</title>\n'
                new_programs += f'    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_programs + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"--- BİTTİ! DMAX: {len(dmax_list)} | TRT 2: {len(trt2_list)} program bulundu. ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
