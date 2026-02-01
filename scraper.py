import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_epg():
    url = "https://www.turksatkablo.com.tr/yayin-akisi.aspx"
    # Tarayıcı gibi görünmek için daha detaylı header
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # GridView tablosunu bul (Türksat bu ID'yi kullanıyor)
        table = soup.find("table", {"id": "ContentPlaceHolder1_gvYayinAkisi"})
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
        
        if table:
            rows = table.find_all("tr")[1:] # İlk satır başlık olduğu için atlıyoruz
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    k_adi = cols[0].text.strip()
                    s_saat = cols[1].text.strip().replace(":", "")
                    p_adi = cols[2].text.strip()
                    
                    tarih = datetime.now().strftime("%Y%m%d")
                    
                    # XMLTV formatına uygun yapı
                    xml_content += f'  <channel id="{k_adi}">\n    <display-name>{k_adi}</display-name>\n  </channel>\n'
                    xml_content += f'  <programme start="{tarih}{s_saat}00 +0300" channel="{k_adi}">\n'
                    xml_content += f'    <title>{p_adi}</title>\n  </programme>\n'
        
        xml_content += "</tv>"
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    fetch_epg()
