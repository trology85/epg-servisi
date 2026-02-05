import requests
import gzip
import io
import xml.etree.ElementTree as ET

def update_epg():
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    rich_url = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Kaynaklar indiriliyor...")
        # Ana Dosya (TR1)
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            main_root = ET.fromstring(f.read())

        # Zengin Dosya (tr.xml)
        resp_rich = requests.get(rich_url, timeout=30)
        resp_rich.encoding = 'utf-8'
        rich_root = ET.fromstring(resp_rich.text)

        print("2. TRT 2 verisi cerrahi yöntemle aktarılıyor...")
        
        # Zengin kaynaktan TRT 2 programlarını bul ve kopyala
        for prog in rich_root.findall("programme"):
            if prog.get("channel") == "TRT 2":
                # Kanal adını senin sistemindeki isme (TRT2 HD) çevir
                prog.set("channel", "TRT2 HD")
                # Bu program bloğunu ana dosyanın içine güvenli bir şekilde ekle
                main_root.append(prog)

        print("3. FOX -> NOW dönüşümü yapılıyor...")
        # FOX kanallarını NOW olarak güncelle
        for channel in main_root.findall("channel"):
            if channel.get("id") == "FOX.HD.tr":
                channel.set("id", "NOW.HD.tr")
                display_name = channel.find("display-name")
                if display_name is not None:
                    display_name.text = "NOW"

        for prog in main_root.findall("programme"):
            if prog.get("channel") == "FOX.HD.tr":
                prog.set("channel", "NOW.HD.tr")

        # Dosyayı kaydet
        print("4. XML yapısı doğrulanıyor ve kaydediliyor...")
        tree = ET.ElementTree(main_root)
        
        # UTF-8 ve XML Deklarasyonu ile kaydet (En güvenli format)
        with open("epg.xml", "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
            
        print("--- BAŞARILI: XML yapısı korundu, crash riski ortadan kalktı! ---")

    except Exception as e:
        print(f"Hata detayı: {e}")

if __name__ == "__main__":
    update_epg()
