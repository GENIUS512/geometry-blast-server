# cloud_server.py
import json
import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LEVELS_DIR = "levels"
MUSIC_DIR = "music"
os.makedirs(LEVELS_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

levels_db = {}
next_id = 1

if os.path.exists("levels_db.json"):
    with open("levels_db.json", "r") as f:
        data = json.load(f)
        levels_db = {int(k): v for k, v in data.get("levels", {}).items()}
        next_id = data.get("next_id", 1)

def save_db():
    with open("levels_db.json", "w") as f:
        json.dump({"levels": levels_db, "next_id": next_id}, f)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Geometry Blast Server is running!"})

@app.route("/api/levels", methods=["GET"])
def get_levels():
    levels_list = []
    for level_id, info in levels_db.items():
        levels_list.append({
            "id": level_id,
            "name": info["name"],
            "author": info["author"],
            "difficulty": info["difficulty"],
            "has_music": info.get("has_music", False),
            "downloads": info.get("downloads", 0)
        })
    return jsonify(levels_list)

@app.route("/api/search", methods=["GET"])
def search_levels():
    query = request.args.get("q", "").strip()
    results = []
    
    if query.isdigit():
        level_id = int(query)
        if level_id in levels_db:
            info = levels_db[level_id]
            results.append({
                "id": level_id,
                "name": info["name"],
                "author": info["author"],
                "difficulty": info["difficulty"]
            })
    else:
        query_lower = query.lower()
        for level_id, info in levels_db.items():
            if query_lower in info["name"].lower():
                results.append({
                    "id": level_id,
                    "name": info["name"],
                    "author": info["author"],
                    "difficulty": info["difficulty"]
                })
    
    return jsonify(results)

@app.route("/api/upload", methods=["POST"])
def upload_level():
    global next_id
    data = request.json
    
    level_name = data.get("name", "Untitled")
    level_author = data.get("author", "Unknown")
    level_difficulty = data.get("difficulty", "Normal")
    level_data = data.get("level_data")
    music_data = data.get("music_data")
    
    level_id = next_id
    next_id += 1
    
    with open(f"{LEVELS_DIR}/level_{level_id}.json", "w") as f:
        json.dump(level_data, f)
    
    has_music = False
    if music_data:
        with open(f"{MUSIC_DIR}/level_{level_id}.mp3", "wb") as f:
            f.write(base64.b64decode(music_data))
        has_music = True
    
    levels_db[level_id] = {
        "name": level_name,
        "author": level_author,
        "difficulty": level_difficulty,
        "has_music": has_music,
        "downloads": 0
    }
    
    save_db()
    print(f"[Server] New level: {level_name} (ID: {level_id}) by {level_author}")
    
    return jsonify({"success": True, "id": level_id})

@app.route("/api/download/<int:level_id>", methods=["GET"])
def download_level(level_id):
    if level_id not in levels_db:
        return jsonify({"error": "Level not found"}), 404
    
    info = levels_db[level_id]
    info["downloads"] = info.get("downloads", 0) + 1
    save_db()
    
    with open(f"{LEVELS_DIR}/level_{level_id}.json", "r") as f:
        level_data = json.load(f)
    
    music_data = None
    if info.get("has_music"):
        with open(f"{MUSIC_DIR}/level_{level_id}.mp3", "rb") as f:
            music_data = base64.b64encode(f.read()).decode("ascii")
    
    return jsonify({
        "level_data": level_data,
        "music_data": music_data,
        "level_name": info["name"],
        "level_author": info["author"]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)