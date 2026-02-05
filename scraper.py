import requests

def update_epg():
    # Sadece senin verdiğin zengin içerikli kaynak
    gold_source = "https://streams.uzunmuhalefet.com/epg/tr.xml"

    try:
        print("1. Kaynak indiriliyor ve karakterler düzeltiliyor...")
        resp = requests.get(gold_source, timeout=60)
        
        # Karakter bozukluğunu önlemek için encoding'i zorla utf-8 yapıyoruz
        resp.encoding = 'utf-8' 
        xml_data = resp.text

        # --- KİMLİK DEĞİŞİMİ (FOX/NOW MANTIĞI) ---
        # Fotoğraftaki TRT 2 HD ismini senin sistemindekiyle eşleştiriyoruz
        replacements = {
            # CNBC-e (Kaynaktaki id="CNBC-e" -> Senin sistemindeki karşılığı)
            'id="CNBC-e"': 'id="CNBC-E"', 
            'channel="CNBC-e"': 'channel="CNBC-E"',
            
            # DMAX
            'id="DMAX"': 'id="DMAX.HD.tr"', 
            'channel="DMAX"': 'channel="DMAX.HD.tr"',
            
            # TRT 2 (Fotoğrafta TRT2 HD görünüyor, ID'yi ona göre mühürleyelim)
            'id="TRT 2"': 'id="TRT2.tr"', 
            'channel="TRT 2"': 'channel="TRT2.tr"',
            
            # FOX/NOW
            'id="FOX"': 'id="NOW.HD.tr"', 
            'channel="FOX"': 'channel="NOW.HD.tr"',
            'id="NOW"': 'id="NOW.HD.tr"', 
            'channel="NOW"': 'channel="NOW.HD.tr"',
        }

        print("2. Kanal isimleri senin listene göre senkronize ediliyor...")
        for old, new in replacements.items():
            xml_data = xml_data.replace(old, new)

        # Dosyayı UTF-8 SIG (BOM) ile kaydedelim ki cihazlar karakterleri doğru okusun
        with open("epg.xml", "w", encoding="utf-8-sig") as f:
            f.write(xml_data)
            
        print("--- İŞLEM TAMAMLANDI ---")

    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    update_epg()
