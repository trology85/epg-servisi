import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_dmax():
    """DMAX'in resmi sitesinden gerçek yayın akışını ve açıklamalarını çeker."""
    url = "https://www.dmax.com.tr/yayin-akisi"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        epg_data = ""
        items = soup.select('.broadcast-item') 
        for item in items:
            time_str = item.select_one('.time').text.strip() if item.select_one('.time') else "00:00"
            title = item.select_one('.title').text.strip() if item.select_one('.title') else "Program"
            desc_el = item.select_one('.description') or item.select_one('.short-description')
            description = desc_el.text.strip() if desc_el else f"{title} programı DMAX ekranlarında."
            
            start_time = datetime.now().strftime("%Y%m%d") + time_str.replace(":", "") + "00 +0300"
            epg_data += f'  <programme start="{start_time}" channel="DMAX.HD.tr">\n'
            epg_data += f'    <title lang="tr">{title}</title>\n'
            epg_data += f'    <desc lang="tr">{description}</desc>\n'
            epg_data += f'  </programme>\n'
        return epg_data
    except:
        return ""

def get_real_trt2():
    """TRT 2'nin resmi sitesinden yayın akışını ve açıklamalarını çeker."""
    url = "https://www.trt2.com.tr/yayin-akisi"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        epg_data = ""
        
        # TRT 2 sitesindeki program bloklarını hedefliyoruz
        items = soup.select('.broadcast-item') or soup.select('.stream-item')
        
        for item in items:
            # Sitedeki saat, başlık ve açıklama alanlarını yakalıyoruz
            time_el = item.select_one('.time')
            title_el = item.select_one('.title') or item.select_one('h3')
            desc_el = item.select_one('.description') or item.select_one('p')
            
            if time_el and title_el:
                time_str = time_el.text.strip()
                title = title_el.text.strip()
                description = desc_el.text.strip() if desc_el else f"{title} programı TRT 2 ekranlarında."
                
                start_time = datetime.now().strftime("%Y%m%d") + time_str.replace(":", "") + "00 +0300"
                
                epg_data += f'  <programme start="{start_time}" channel="TRT2.HDtr">\n'
                epg_data += f'    <title lang="tr">{title}</title>\n'
                epg_data += f'    <desc lang="tr">{description}</desc>\n'
                epg_data += f'  </programme>\n'
        return epg_data
    except Exception as e:
        print(f"TRT 2 hatası: {e}")
        return ""

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    
    try:
        print("1. Ana EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')
        
        # FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('>FOX HD<', '>NOW HD<')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # Eski DMAX verilerini temizle
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        
        # TRT 2 kanalı dosyada hiç yoksa kanal tanımını ekleyelim (Opsiyonel ama garantici yol)
        if 'id="TRT2.tr"' not in xml_content:
            trt2_channel_tag = '  <channel id="TRT2.tr">\n    <display-name lang="tr">TRT 2 HD</display-name>\n  </channel>\n'
            xml_content = xml_content.replace('</tv>', trt2_channel_tag + '</tv>')

        print("2. DMAX ve TRT 2 verileri web sitelerinden kazınıyor...")
        extra_epg = get_real_dmax() + get_real_trt2()
        
        print("3. Boş açıklamalar için otomatik yama yapılıyor...")
        # Başlığı olan ama açıklaması olmayan programlara otomatik açıklama ekler
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Yayın akışı detayları ve program özeti.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        # Yeni verileri en sona ekle
        xml_content = xml_content.replace('</tv>', extra_epg + '\n</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print("--- İŞLEM TAMAMLANDI ---")
        print("Dosya: epg.xml hazır.")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
