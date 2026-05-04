# cloud_server.py
import json
import os
import base64
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LEVELS_DIR = "levels"
MUSIC_DIR = "music"
os.makedirs(LEVELS_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# База данных уровней
levels_db = {}
next_id = 1

if os.path.exists("levels_db.json"):
    with open("levels_db.json", "r") as f:
        data = json.load(f)
        levels_db = {int(k): v for k, v in data.get("levels", {}).items()}
        next_id = data.get("next_id", 1)

# База данных пользователей
users_db = {}
next_user_id = 1

if os.path.exists("users_db.json"):
    with open("users_db.json", "r") as f:
        data = json.load(f)
        users_db = {int(k): v for k, v in data.get("users", {}).items()}
        next_user_id = data.get("next_user_id", 1)

def save_levels_db():
    with open("levels_db.json", "w") as f:
        json.dump({"levels": levels_db, "next_id": next_id}, f)

def save_users_db():
    with open("users_db.json", "w") as f:
        json.dump({"users": users_db, "next_user_id": next_user_id}, f)

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
    
    save_levels_db()
    print(f"[Server] New level: {level_name} (ID: {level_id}) by {level_author}")
    
    return jsonify({"success": True, "id": level_id})

@app.route("/api/download/<int:level_id>", methods=["GET"])
def download_level(level_id):
    if level_id not in levels_db:
        return jsonify({"error": "Level not found"}), 404
    
    info = levels_db[level_id]
    info["downloads"] = info.get("downloads", 0) + 1
    save_levels_db()
    
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

# ========== АККАУНТЫ ==========

@app.route("/api/register", methods=["POST"])
def register():
    global next_user_id
    data = request.json
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"})
    
    for user in users_db.values():
        if user["username"] == username:
            return jsonify({"success": False, "error": "Username already exists"})
    
    user_id = next_user_id
    next_user_id += 1
    
    users_db[user_id] = {
        "id": user_id,
        "username": username,
        "password": password,
        "created_at": time.time()
    }
    
    save_users_db()
    print(f"[Server] New user: {username} (ID: {user_id})")
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "username": username
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    for user in users_db.values():
        if user["username"] == username and user["password"] == password:
            print(f"[Server] User logged in: {username}")
            return jsonify({
                "success": True,
                "user_id": user["id"],
                "username": user["username"]
            })
    
    return jsonify({"success": False, "error": "Invalid username or password"})

@app.route("/api/complete_level/<int:level_id>", methods=["POST"])
def complete_level():
    """Увеличивает счётчик прохождений уровня"""
    level_id = request.view_args.get('level_id')
    
    if level_id not in levels_db:
        return jsonify({"error": "Level not found"}), 404
    
    levels_db[level_id]["completed"] = levels_db[level_id].get("completed", 0) + 1
    save_levels_db()
    
    return jsonify({"success": True, "completed": levels_db[level_id]["completed"]})

@app.route("/api/delete_level/<int:level_id>", methods=["DELETE"])
def delete_level(level_id):
    """Удаляет уровень с сервера (только для владельца)"""
    # Получаем имя пользователя из запроса
    data = request.json
    username = data.get("username", "")
    
    if level_id not in levels_db:
        return jsonify({"error": "Level not found"}), 404
    
    level = levels_db[level_id]
    
    # Проверяем, является ли пользователь владельцем
    if level["author"] != username:
        return jsonify({"error": "You can only delete your own levels"}), 403
    
    # Удаляем файлы
    level_path = f"{LEVELS_DIR}/level_{level_id}.json"
    music_path = f"{MUSIC_DIR}/level_{level_id}.mp3"
    
    if os.path.exists(level_path):
        os.remove(level_path)
    if os.path.exists(music_path):
        os.remove(music_path)
    
    # Удаляем из базы
    del levels_db[level_id]
    save_levels_db()
    
    print(f"[Server] Level {level_id} deleted by {username}")
    
    return jsonify({"success": True, "message": "Level deleted"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
