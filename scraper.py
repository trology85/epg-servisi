import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_epg():
    url = "https://www.turksatkablo.com.tr/yayin-akisi.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.turksatkablo.com.tr/"
    }
    
    try:
        # Siteye bağlan
        session = requests.Session()
        response = session.get(url, headers=headers, verify=False, timeout=30)
        
        print(f"Site Yanıt Kodu: {response.status_code}") # Hata ayıklama için
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Türksat bazen veriyi farklı bir class altında saklıyor olabilir.
        # En geniş kapsamlı seçiciyi kullanalım.
        rows = soup.find_all("tr", class_=["alt", "none"]) # Türksat'ın kullandığı satır sınıfları
        
        # Eğer yukarıdaki bulamazsa genel tabloyu dene
        if not rows:
            table = soup.find("table", {"id": "ContentPlaceHolder1_gvYayinAkisi"})
            if table:
                rows = table.find_all("tr")[1:]

        print(f"Bulunan Satır Sayısı: {len(rows)}") # Burası 0 ise içerik gelmiyordur

        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
        
        count = 0
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                k_adi = cols[0].text.strip()
                s_saat = cols[1].text.strip().replace(":", "")
                p_adi = cols[2].text.strip()
                
                if k_adi and p_adi:
                    tarih = datetime.now().strftime("%Y%m%d")
                    xml_content += f'  <channel id="{k_adi}">\n    <display-name>{k_adi}</display-name>\n  </channel>\n'
                    xml_content += f'  <programme start="{tarih}{s_saat}00 +0300" channel="{k_adi}">\n'
                    xml_content += f'    <title>{p_adi}</title>\n  </programme>\n'
                    count += 1
        
        xml_content += "</tv>"
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"İşlem tamamlandı. {count} adet program eklendi.")
            
    except Exception as e:
        print(f"Hata detayı: {e}")

if __name__ == "__main__":
    fetch_epg()
