import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []

        # CNBC-E için özel kontrol (cnbce.com)
        if "cnbce" in url:
            # Sitedeki tüm metinleri tara ve 00:00 formatını yakala
            # CNBC-e genelde <div> içinde başlık ve saat tutar
            for item in soup.find_all(['div', 'li'], class_=re.compile(r'(item|program|card|list)', re.I)):
                time_txt = ""
                title_txt = ""
                
                # Saat formatını (HH:MM) ara
                time_search = item.find(string=re.compile(r'^\d{2}[:\.]\d{2}$'))
                if time_search:
                    time_txt = time_search.strip().replace('.', ':')
                    # Saat bulunan yerin yakınındaki başlığı ara
                    title_el = item.find(['h2', 'h3', 'h4', 'span', 'strong', 'p'])
                    if title_el:
                        title_txt = title_el.get_text(strip=True)
                
                if time_txt and title_txt and len(title_txt) > 2:
                    if not any(p['time'] == time_txt for p in programs):
                        programs.append({'time': time_txt, 'title': title_txt})

        # DMAX için özel kontrol (dmax.com.tr)
        elif "dmax" in url:
            for item in soup.select('.broadcast-item, .program-item, .card'):
                time_el = item.select_one('.time, .hour')
                title_el = item.select_one('.title, .name, h3')
                if time_el and title_el:
                    programs.append({
                        'time': time_el.get_text(strip=True).replace('.', ':'),
                        'title': title_el.get_text(strip=True)
                    })

        # Eğer hala 0 ise (Son çare: Tüm sayfadaki HH:MM düzenini yakala)
        if not programs:
            all_text = soup.get_text("|", strip=True)
            # 12:30|Program Adı gibi bir yapı arayalım
            matches = re.findall(r'(\d{2}[:\.]\d{2})\|([^\|]{3,50})', all_text)
            for m in matches:
                programs.append({'time': m[0].replace('.', ':'), 'title': m[1].strip()})

        return programs
    except Exception as e:
        print(f"Hata: {e}")
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

        # --- GÜVENLİ TEMİZLİK VE KANAL TANIMLAMA ---
        target_channels = {
            "DMAX.HD.tr": "https://www.dmax.com.tr/yayin-akisi",
            "CNBC-E": "https://www.cnbce.com/yayin-akisi"
        }

        for cid in target_channels:
            xml_content = re.sub(f'<programme[^>]+channel="{re.escape(cid)}".*?</programme>', '', xml_content, flags=re.DOTALL)
            if f'id="{cid}"' not in xml_content:
                xml_content = xml_content.replace('</tv>', f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n</tv>')

        print("2. Veriler web'den çekiliyor...")
        new_programs_xml = ""
        today = datetime.now().strftime("%Y%m%d")

        for cid, url in target_channels.items():
            data_list = get_real_web_data(url)
            print(f"> {cid} için {len(data_list)} program bulundu.")
            for p in data_list:
                start = f"{today}{p['time'].replace(':', '')}00 +0300"
                new_programs_xml += f'  <programme start="{start}" channel="{cid}">\n'
                new_programs_xml += f'    <title lang="tr">{p["title"]}</title>\n'
                new_programs_xml += f'    <desc lang="tr">{p["title"]} programı {cid} ekranlarında.</desc>\n'
                new_programs_xml += f'  </programme>\n'

        # Boş açıklamaları doldur (Diğer kanallar)
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        xml_content = re.sub(pattern, r'\1\n    <desc lang="tr">Yayın akışı detayları.</desc>', xml_content, flags=re.DOTALL)

        xml_content = xml_content.replace('</tv>', new_programs_xml + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Genel hata: {e}")

if __name__ == "__main__":
    update_epg()
