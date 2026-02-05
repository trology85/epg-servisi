import requests
import gzip
import io
import re

def update_epg():
    # 1. ANA KAYNAK: Tüm kanalların doğru saatli listesi
    main_url = "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
    # 2. ZENGİN KAYNAK: Sadece TRT 2'nin detaylı açıklamalarını buradan alacağız
    rich_url = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Kaynaklar indiriliyor...")
        # Ana listeyi indir ve aç
        resp_main = requests.get(main_url, timeout=30)
        with gzip.GzipFile(fileobj=io.BytesIO(resp_main.content)) as f:
            xml_main = f.read().decode('utf-8')

        # Zengin listeyi indir
        resp_rich = requests.get(rich_url, timeout=30)
        resp_rich.encoding = 'utf-8'
        xml_rich = resp_rich.text

        print("2. TRT 2 içeriği ayıklanıyor ve 'TRT2 HD' olarak etiketleniyor...")
        
        # Zengin kaynaktaki kanal adı "TRT 2" olarak geçiyor. 
        # Onu bulup senin sistemindeki "TRT2 HD"ye çeviriyoruz.
        trt2_pattern = r'<programme[^>]+channel="TRT 2".*?</programme>'
        trt2_matches = re.findall(trt2_pattern, xml_rich, flags=re.DOTALL)
        
        trt2_custom_content = ""
        for m in trt2_matches:
            # Kanal ismini senin cihazındaki isme (TRT2 HD) tam olarak eşliyoruz
            fixed_p = m.replace('channel="TRT 2"', 'channel="TRT2 HD"')
            trt2_custom_content += fixed_p + "\n"

        # --- DÜZELTMELER ---
        # 1. Ana listedeki FOX'u NOW yapalım (senin sistemin için gerekliyse)
        xml_main = xml_main.replace('id="FOX.HD.tr"', 'id="NOW.HD.tr"').replace('channel="FOX.HD.tr"', 'channel="NOW.HD.tr"')
        
        # 2. Eğer ana listede TRT 2 zaten varsa (açıklamasız hali), çakışma olmasın diye onu temizleyebiliriz
        # Ama şimdilik sadece sonuna eklemek de işe yarayacaktır.
        
        # Birleştirme: Tüm listeyi al, kapanıştan hemen önce bizim zengin TRT 2'yi enjekte et
        final_xml = xml_main.replace("</tv>", trt2_custom_content + "</tv>")

        print("3. Dosya 'utf-8-sig' ile mühürleniyor (Karakter sorunu için)...")
        with open("epg.xml", "w", encoding="utf-8-sig") as f:
            f.write(final_xml)
            
        print("--- BAŞARILI: TRT2 HD açıklamalarıyla eklendi, diğer kanallar korundu! ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
