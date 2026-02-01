import requests
import json
from datetime import datetime

def fetch_epg():
    # Türksat'ın veriyi çektiği asıl API ucu
    url = "https://www.turksatkablo.com.tr/Web_Services/TurksatWebServices.ashx"
    
    # API'ye gönderilecek özel komut (Yayın akışını getir der)
    params = {
        "islem": "YayinAkisi",
        "tarih": datetime.now().strftime("%d.%m.%Y")
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.turksatkablo.com.tr/yayin-akisi.aspx"
    }

    try:
        response = requests.get(url, params=params, headers=headers, verify=False)
        # Gelen veri JSON formatında olacak
        data = response.json()
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
        
        # JSON verisini döngüye sokup XML formatına çeviriyoruz
        for item in data:
            kanal = item.get("KanalAd", "Bilinmeyen Kanal")
            program = item.get("YayinAd", "Program Bilgisi Yok")
            saat = item.get("YayinSaat", "00:00").replace(":", "")
            tarih = datetime.now().strftime("%Y%m%d")
            
            xml_content += f'  <channel id="{kanal}">\n    <display-name>{kanal}</display-name>\n  </channel>\n'
            xml_content += f'  <programme start="{tarih}{saat}00 +0300" channel="{kanal}">\n'
            xml_content += f'    <title>{program}</title>\n  </programme>\n'
        
        xml_content += "</tv>"
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"Başarılı! {len(data)} adet yayın bilgisi çekildi.")

    except Exception as e:
        print(f"API Hatası: {e}")

if __name__ == "__main__":
    fetch_epg()
