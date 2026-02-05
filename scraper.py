import requests
import gzip
import io

def update_epg():
    # SAATLERİ VE İÇERİĞİ DOĞRU OLAN ANA KAYNAK
    source_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"

    try:
        print("1. Güvenilir kaynak indiriliyor (Gzip)...")
        resp = requests.get(source_url, timeout=30)
        
        # Gzip dosyasını açıp içeriği okuyoruz
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
            xml_data = f.read().decode('utf-8')

        # --- SADECE GEREKLİ DÜZELTMELER ---
        # FOX -> NOW dönüşümü (Saatlere dokunmuyoruz, zaten +3 geliyor)
        replacements = {
            'id="FOX.HD.tr"': 'id="NOW.HD.tr"',
            'channel="FOX.HD.tr"': 'channel="NOW.HD.tr"',
            
            # Eğer listede CNBC-E ve DMAX isimleri farklıysa buraya ekleyebiliriz
            'id="CNBC-e"': 'id="CNBC-E"',
            'channel="CNBC-e"': 'channel="CNBC-E"',
            'id="DMAX.tr"': 'id="DMAX.HD.tr"',
            'channel="DMAX.tr"': 'channel="DMAX.HD.tr"'
        }

        print("2. Kanal isimleri senkronize ediliyor...")
        for old, new in replacements.items():
            xml_data = xml_data.replace(old, new)

        # Dosyayı kaydediyoruz
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_data)
            
        print("--- BAŞARILI: İlk kaynağa dönüldü, saatler ve içerikler artık doğru. ---")

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    update_epg()
