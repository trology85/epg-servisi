import requests
from bs4 import BeautifulSoup
import gzip
import io
import re
from datetime import datetime

def get_real_dmax():
    """DMAX'in resmi sitesinden gerçek yayın akışını ve açıklamalarını çeker."""
    url = "https://www.dmax.com.tr/yayin-akisi"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.encoding = 'utf-8' # Türkçe karakterler için zorunlu
        soup = BeautifulSoup(r.content, 'html.parser')
        epg_data = ""
        
        # DMAX sitesindeki yayın blokları
        items = soup.select('.broadcast-item') 
        for item in items:
            time_str = item.select_one('.time').text.strip() if item.select_one('.time') else "00:00"
            title = item.select_one('.title').text.strip() if item.select_one('.title') else "Program"
            
            # --- AÇIKLAMA (DESC) ÇEKME ---
            # DMAX sitesinde açıklama genelde .description veya .short-description class'ındadır.
            desc_el = item.select_one('.description')
            if not desc_el:
                desc_el = item.select_one('.short-description')
            
            description = desc_el.text.strip() if desc_el else f"{title} programı DMAX ekranlarında."
            
            # Zamanı XML formatına çevir (Bugünün tarihi + saat)
            start_time = datetime.now().strftime("%Y%m%d") + time_str.replace(":", "") + "00 +0300"
            
            epg_data += f'  <programme start="{start_time}" channel="DMAX.HD.tr">\n'
            epg_data += f'    <title lang="tr">{title}</title>\n'
            epg_data += f'    <desc lang="tr">{description}</desc>\n'
            epg_data += f'  </programme>\n'
        return epg_data
    except Exception as e:
        print(f"DMAX kazıma hatası: {e}")
        return ""

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    
    try:
        print("EPG indiriliyor...")
        resp = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_content = f.read().decode('utf-8')
        
        # 1. FOX -> NOW Değişimi
        print("Kanal isimleri güncelleniyor (FOX -> NOW)...")
        xml_content = xml_content.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"')
        xml_content = xml_content.replace('>FOX HD<', '>NOW HD<')
        xml_content = xml_content.replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')

        # 2. Bozuk DMAX verilerini temizle
        print("Eski DMAX verileri temizleniyor...")
        xml_content = re.sub(r'<programme[^>]+channel="DMAX\.HD\.tr".*?</programme>', '', xml_content, flags=re.DOTALL)
        
        # 3. Gerçek DMAX verilerini çek ve ekle
        print("DMAX resmi sitesinden açıklamalı veriler alınıyor...")
        real_dmax_xml = get_real_dmax()
        
        # 4. Eksik Açıklamaları Otomatik Doldurma (Genel Kontrol)
        # Eğer bir programda <desc> etiketi yoksa, sistemin boş görünmemesi için ekliyoruz.
        print("Genel eksik açıklamalar kontrol ediliyor...")
        # Bu regex, içinde desc olmayan programme bloklarını bulur
        pattern = r'(<programme[^>]*>\s*<title[^>]*>.*?</title>)(?!\s*<desc)'
        replacement = r'\1\n    <desc lang="tr">Program detayları ve canlı yayın akışı.</desc>'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)

        # Verileri </tv> etiketinden hemen önceye yapıştır
        xml_content = xml_content.replace('</tv>', real_dmax_xml + '\n</tv>')

        # 5. Dosyayı Kaydet
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print("--- İşlem Başarılı! ---")
        print("1. NOW (Fox) dönüşümü tamam.")
        print("2. DMAX açıklamalı olarak eklendi.")
        print("3. Diğer kanallardaki boş açıklamalar dolduruldu.")

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    update_epg()
