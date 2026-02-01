import requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_epg():
    url = "https://www.turksatkablo.com.tr/yayin-akisi.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # XML Başlangıcı
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
    
    rows = soup.select("table#ContentPlaceHolder1_gvYayinAkisi tr")
    for row in rows:
        kanal = row.select_one("td.program_kanal")
        saat = row.select_one("td.program_saat")
        program = row.select_one("td.program_adi")
        
        if kanal and saat and program:
            k_adi = kanal.text.strip()
            s_saat = saat.text.strip().replace(":", "")
            p_adi = program.text.strip()
            # Basit bir tarih eklemesi (Bugünün tarihi + saat)
            tarih = datetime.now().strftime("%Y%m%d")
            
            xml_content += f'  <channel id="{k_adi}">\n    <display-name>{k_adi}</display-name>\n  </channel>\n'
            xml_content += f'  <programme start="{tarih}{s_saat}00 +0300" channel="{k_adi}">\n'
            xml_content += f'    <title>{p_adi}</title>\n  </programme>\n'
            
    xml_content += "</tv>"
    
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

if __name__ == "__main__":
    fetch_epg()
