import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_web_data(url):
    # Daha gerçekçi bir tarayıcı kimliği
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.encoding = 'utf-8'
        if r.status_code != 200:
            print(f"Siteye erişilemedi: {url} (Kod: {r.status_code})")
            return []
            
        soup = BeautifulSoup(r.content, 'html.parser')
        programs = []
        
        # TRT 2 ÖZEL: Sitedeki akış listesini kapsayan div'leri bulmaya çalışalım
        # TRT sitesi bazen 'li' etiketleri içinde 'span' kullanır.
        items = soup.find_all(['div', 'li', 'tr'], class_=re.compile(r'(item|broadcast|stream|card|timeline)'))
        
        for item in items:
            # Zamanı bul (00:00 formatı için her yere bak)
            time_el = item.find(string=re.compile(r'^\d{2}[:\.]\d{2}$'))
            # Başlığı bul (Genelde h3, h4 veya güçlü yazılmış span olur)
            title_el = item.find(['h2', 'h3', 'h4', 'span', 'div'], class_=re.compile(r'(title|name|subject)'))
            
            if time_el and title_el:
                time_str = time_el.strip().replace('.', ':')
                title_str = title_el.get_text(strip=True)
                
                # Tekrar eden verileri engellemek için kontrol
                if not any(p['time'] == time_str for p in programs):
                    programs.append({
                        'time': time_str,
                        'title': title_str,
                        'desc': title_str + " - TRT 2 ekranlarında yayınlanmaktadır." # Basit bir açıklama oluştur
                    })
        
        return sorted(programs, key=lambda x: x['time'])
    except Exception as e:
        print(f"Hata: {url} kazınırken hata oluştu: {e}")
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

        # --- GÜVENLİ TEMİZLİK ---
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        
        # Sadece TRT 2 ID'lerini temizle, diğer TRT'lere dokunma
        custom_ids = ["TRT 2", "TRT2.tr", "TRT 2 HD"]
        for cid in custom_ids:
            # Nokta atışı temizlik
            xml_content = re.sub(f'<programme[^>]+channel="{re.escape(cid)}".*?</programme>', '', xml_content, flags=re.DOTALL)
            # Kanal tanımını da yenilemek için eğer varsa silip sonra ekleyelim
            xml_content = re.sub(f'<channel id="{re.escape(cid)}".*?</channel>', '', xml_content, flags=re.DOTALL)

        # Kanal Tanımlarını Ekle
        trt_defs = ""
        for cid in custom_ids:
            trt_defs += f'  <channel id="{cid}">\n    <display-name lang="tr">{cid}</display-name>\n  </channel>\n'
        xml_content = xml_content.replace('</tv>', trt_defs + '</tv>')

        print("2. Veriler çekiliyor...")
        dmax_list = get_real_web_data("https://www.dmax.com.tr/yayin-akisi")
        trt2_list = get_real_web_data("https://www.trt2.com.tr/yayin-akisi")

        new_programs = ""
        today = datetime.now().strftime("%Y%m%d")

        # DMAX Ekleme
        for p in dmax_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            new_programs += f'  <programme start="{start}" channel="DMAX.HD.tr">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        # TRT 2 Ekleme
        for p in trt2_list:
            start = f"{today}{p['time'].replace(':', '')}00 +0300"
            for cid in custom_ids:
                new_programs += f'  <programme start="{start}" channel="{cid}">\n    <title lang="tr">{p["title"]}</title>\n    <desc lang="tr">{p["desc"]}</desc>\n  </programme>\n'

        xml_content = xml_content.replace('</tv>', new_programs + '</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print(f"--- SONUÇ --- DMAX: {len(dmax_list)} | TRT 2: {len(trt2_list)} program.")

    except Exception as e:
        print(f"Genel hata: {e}")

if __name__ == "__main__":
    update_epg()
