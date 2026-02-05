import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_dmax():
    """DMAX'in resmi sitesinden gerçek yayın akışını çeker."""
    url = "https://www.dmax.com.tr/yayin-akisi"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        epg_data = ""
        
        # Sitedeki her bir yayın satırını bul (DMAX'in güncel sitesine göre ayarlandı)
        items = soup.select('.broadcast-item') # Sitenin yapısına göre güncellendi
        for item in items:
            time_str = item.select_one('.time').text.strip() # Örn: 21:00
            title = item.select_one('.title').text.strip()
            
            # Zamanı XML formatına çevir (Bugünün tarihi + saat)
            start_time = datetime.now().strftime("%Y%m%d") + time_str.replace(":", "") + "00 +0300"
            
            epg_data += f'  <programme start="{start_time}" channel="DMAX.HD.tr">\n'
            epg_data += f'    <title lang="tr">{title}</title>\n'
            epg_data += f'  </programme>\n'
        return epg_data
    except:
        return ""

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    
    try:
        print("EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')
        
        # 1. FOX -> NOW Değişimi
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('>FOX HD<', '>NOW HD<')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # 2. Bozuk DMAX verilerini temizle
        print("Bozuk DMAX verileri siliniyor...")
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        
        # 3. Gerçek DMAX verilerini çek ve ekle
        print("DMAX resmi sitesinden güncel veriler alınıyor...")
        real_dmax_xml = get_real_dmax()
        
        # Verileri </tv> etiketinden hemen önceye yapıştır
        xml_content = xml_content.replace('</tv>', real_dmax_xml + '\n</tv>')

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print("İşlem Başarılı! NOW güncellendi, DMAX tamir edildi.")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
