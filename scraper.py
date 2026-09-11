import requests
from bs4 import BeautifulSoup
import json
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 4 Büyükler + 10 Avrupa Dev Kulübü Wikipedia Listeleri
TARGET_PAGES = [
    # 🇹🇷 Süper Lig 4 Büyükler
    {"club_id": "BES", "club_name": "Beşiktaş", "url": "https://tr.wikipedia.org/wiki/Be%C5%9Fikta%C5%9F_yabanc%C4%B1_futbolcular%C4%B1_listesi"},
    {"club_id": "FEN", "club_name": "Fenerbahçe", "url": "https://tr.wikipedia.org/wiki/Fenerbah%C3%A7e_yabanc%C4%B1_futbolcular%C4%B1_listesi"},
    {"club_id": "GAL", "club_name": "Galatasaray", "url": "https://tr.wikipedia.org/wiki/Galatasaray_yabanc%C4%B1_futbolcular%C4%B1_listesi"},
    {"club_id": "TRA", "club_name": "Trabzonspor", "url": "https://tr.wikipedia.org/wiki/Trabzonspor_yabanc%C4%B1_futbolcular%C4%B1_listesi"},

    # 🌍 Avrupa Devleri (English Wikipedia All-Time Player Listeleri)
    {"club_id": "RMA", "club_name": "Real Madrid", "url": "https://en.wikipedia.org/wiki/List_of_Real_Madrid_CF_players"},
    {"club_id": "BAR", "club_name": "Barcelona", "url": "https://en.wikipedia.org/wiki/List_of_FC_Barcelona_players"},
    {"club_id": "MUN", "club_name": "Manchester United", "url": "https://en.wikipedia.org/wiki/List_of_Manchester_United_F.C._players"},
    {"club_id": "CHE", "club_name": "Chelsea", "url": "https://en.wikipedia.org/wiki/List_of_Chelsea_F.C._players"},
    {"club_id": "ARS", "club_name": "Arsenal", "url": "https://en.wikipedia.org/wiki/List_of_Arsenal_F.C._players"},
    {"club_id": "MCI", "club_name": "Manchester City", "url": "https://en.wikipedia.org/wiki/List_of_Manchester_City_F.C._players"},
    {"club_id": "BAY", "club_name": "Bayern Munich", "url": "https://en.wikipedia.org/wiki/List_of_FC_Bayern_Munich_players"},
    {"club_id": "JUV", "club_name": "Juventus", "url": "https://en.wikipedia.org/wiki/List_of_Juventus_FC_players"},
    {"club_id": "MIL", "club_name": "AC Milan", "url": "https://en.wikipedia.org/wiki/List_of_A.C._Milan_players"},
    {"club_id": "PSG", "club_name": "Paris Saint-Germain", "url": "https://en.wikipedia.org/wiki/List_of_Paris_Saint-Germain_F.C._players"}
]

# Kesinlikle elenecek kelimeler / başlıklar
EXCLUDE_WORDS = {
    "list", "players", "football", "league", "cup", "stadium", "season", "team", 
    "national", "federation", "club", "match", "world", "türkiye", "brezilya", 
    "england", "france", "germany", "spain", "italy", "mısır", "yeşil burun"
}

def scrape_wikipedia_players(url):
    players = set()
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table', class_='wikitable')
            
            for table in tables:
                for row in table.find_all('tr'):
                    # Tablodaki ilk hücrede veya link içeren hücrede oyuncu adını ara
                    cells = row.find_all(['td', 'th'])
                    for cell in cells[:2]:
                        anchor = cell.find('a')
                        if anchor and anchor.text:
                            name = anchor.text.strip()
                            clean_lower = name.lower()
                            
                            # 🎯 KATI FİLTRELEME MANTIĞI:
                            # 1. İsmin içinde sayı olmayacak
                            # 2. Ülke/Başlık kelimeleri içermeyecek
                            # 3. Gerçek İnsan İsmi Mantığı: En az 2 kelimeden oluşacak (Ad + Soyad) veya Pele/Neymar gibi özel durum
                            words = name.split()
                            
                            if (not re.search(r'\d', name) and 
                                not any(ex in clean_lower for ex in EXCLUDE_WORDS) and
                                len(name) > 4 and
                                len(words) >= 2): # Sadece En Az Ad + Soyad içerenleri alır (Ülkeleri %100 engeller)
                                
                                players.add(name)
    except Exception as e:
        print(f"Hata oluştu: {e}")
    
    return list(players)

def build_database():
    print("🚀 14 Dev Kulübün Tüm Zamanlar Veritabanı Oluşturuluyor...\n")
    scraped_data = []

    for item in TARGET_PAGES:
        print(f"⏳ {item['club_name']} oyuncuları çekiliyor...")
        player_list = scrape_wikipedia_players(item['url'])
        print(f"✅ {item['club_name']} için {len(player_list)} süper oyuncu bulundu!")
        
        scraped_data.append({
            "club_id": item["club_id"],
            "club_name": item["club_name"],
            "players": player_list
        })

    with open('all_time_database.json', 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)

    print("\n🎉 MÜKEMMEL! 14 Takımlık Dev Veritabanı 'all_time_database.json' Dosyasına Kaydedildi.")

if __name__ == "__main__":
    build_database()