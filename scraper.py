import requests
import gzip
import io
import os

def update_epg():
    # 1. Kaynak EPG linki (GZ formatında)
    url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    
    try:
        print("Dosya indiriliyor...")
        response = requests.get(url, timeout=30)
        
        # 2. GZ dosyasını hafızada aç
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            xml_content = f.read().decode('utf-8')
        
        # 3. İSİM DEĞİŞTİRME (Düzenleme kısmı burası)
        # FOX gördüğü her yeri NOW yapar. 
        # Bunu kanal ID'si ve display name için yapıyoruz.
        print("Kanal isimleri güncelleniyor...")
        xml_content = xml_content.replace('display-name>FOX', 'display-name>NOW')
        xml_content = xml_content.replace('channel="FOX"', 'channel="NOW"')
        xml_content = xml_content.replace('id="FOX"', 'id="NOW"')

        # Başka değiştirmek istediğin kanal varsa buraya ekleyebilirsin:
        # xml_content = xml_content.replace('Eski Kanal', 'Yeni Kanal')

        # 4. Yeni XML dosyası olarak kaydet
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        print("İşlem başarıyla tamamlandı. epg.xml oluşturuldu.")

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    update_epg()
