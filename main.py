from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import unicodedata
from typing import Dict
from fastapi import FastAPI,WebSocket,WebSocketDisconnect

app = FastAPI()

# Web sitenin (JavaScript) bu API'ye erişebilmesi için CORS izni veriyoruz
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metin temizleme (Eşleşmeleri kolaylaştırmak için)
def sanitize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower()
    nfkd = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return only_ascii.strip()

# JSON dosyasındaki veritabanını yüklüyoruz
def load_db():
    with open('all_time_database.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/api/get-match")
def get_match():
    db = load_db()
    
    # Sürekli ortak oyuncusu olan 2 takım bulana kadar döngü döner
    while True:
        clubA = random.choice(db)
        clubB = random.choice(db)
        
        # Aynı takımlar seçilirse tekrar seç
        if clubA["club_id"] == clubB["club_id"]:
            continue
            
        playersA = clubA["players"]
        playersB = clubB["players"]
        
        # İki takımın ortak oyuncularını buluyoruz
        common_players = []
        for pA in playersA:
            cleanA = sanitize(pA)
            for pB in playersB:
                cleanB = sanitize(pB)
                # İsimler tam eşleşiyorsa veya birbirini kapsıyorsa doğru cevaptır
                if cleanA == cleanB:
              
             
                    common_players.append(pA)
                    break
        
        # Eğer en az 1 ortak oyuncu bulunduysa bu soruyu döndür
        if len(common_players) > 0:
            return {
                "clubA": {
                    "id": clubA["club_id"],
                    "name": clubA["club_name"],
                    "league": "All-Time",
                    "color": "#123526"
                },
                "clubB": {
                    "id": clubB["club_id"],
                    "name": clubB["club_name"],
                    "league": "All-Time",
                    "color": "#1B4E36"
                },
                "answers": list(set(common_players)) # Doğru cevaplar listesi
                
            }
        # Aktif odaları RAM'de tutan yapı
rooms: Dict[str, dict] = {}

def pick_valid_match():
    db = load_db()
    while True:
        clubA = random.choice(db)
        clubB = random.choice(db)
        if clubA["club_id"] == clubB["club_id"]:
            continue

        playersA = clubA["players"]
        playersB = clubB["players"]
        common = []
        for pA in playersA:
            cleanA = sanitize(pA)
            for pB in playersB:
                cleanB = sanitize(pB)
                if cleanA == cleanB:
                    common.append(pA)
                    break

        if len(common) > 0:
            return {
                "clubA": {"id": clubA["club_id"], "name": clubA["club_name"]},
                "clubB": {"id": clubB["club_id"], "name": clubB["club_name"]},
                "common_players": common
            }

@app.websocket("/ws/{room_id}/{player_name}")
async def game_socket(websocket: WebSocket, room_id: str, player_name: str):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = {
            "players": {},
            "scores": {},
            "current_match": None,
            "target_score": 5
        }

    room = rooms[room_id]

    # Odaya en fazla 2 kişi girebilir
    if len(room["players"]) >= 2 and player_name not in room["players"]:
        await websocket.send_json({"type": "ERROR", "msg": "Oda dolu!"})
        await websocket.close()
        return

    room["players"][player_name] = websocket
    if player_name not in room["scores"]:
        room["scores"][player_name] = 0

    # Odaya katılım bildirimi
    for ws in room["players"].values():
        await ws.send_json({
            "type": "ROOM_STATUS",
            "players": list(room["players"].keys())
        })

    # 2 kişi tamamlandığında ilk soruyu üret ve oyunu başlat
    if len(room["players"]) == 2 and room["current_match"] is None:
        room["current_match"] = pick_valid_match()
        for ws in room["players"].values():
            await ws.send_json({
                "type": "ROUND_START",
                "clubA": room["current_match"]["clubA"],
                "clubB": room["current_match"]["clubB"],
                "scores": room["scores"]
            })

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "SUBMIT_ANSWER":
                guess = sanitize(data.get("guess", ""))
                common_sanitized = [sanitize(p) for p in room["current_match"]["common_players"]]

                if guess in common_sanitized:
                    room["scores"][player_name] += 1
                    winner = player_name

                    for ws in room["players"].values():
                        await ws.send_json({
                            "type": "ROUND_WIN",
                            "winner": winner,
                            "scores": room["scores"],
                            "common_players": room["current_match"]["common_players"]
                        })

                    if room["scores"][player_name] >= room["target_score"]:
                        for ws in room["players"].values():
                            await ws.send_json({"type": "GAME_OVER", "winner": winner})
                        rooms.pop(room_id, None)
                        break
                    else:
                        room["current_match"] = pick_valid_match()
                        for ws in room["players"].values():
                            await ws.send_json({
                                "type": "ROUND_START",
                                "clubA": room["current_match"]["clubA"],
                                "clubB": room["current_match"]["clubB"],
                                "scores": room["scores"]
                            })
                else:
                    await websocket.send_json({"type": "WRONG_ANSWER"})

    except WebSocketDisconnect:
        if room_id in rooms:
            rooms[room_id]["players"].pop(player_name, None)
            if len(rooms[room_id]["players"]) == 0:
                rooms.pop(room_id, None)
            else:
                for ws in rooms[room_id]["players"].values():
                    await ws.send_json({"type": "PLAYER_LEFT", "player": player_name})
    
                

