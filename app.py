"""
BlinkRun Local Backend
========================
- Saves player photos  →  ./player_photos/
- Saves all data       →  ./game_data.json
- No database, no cloud, 100% offline
"""

import os, json, base64, uuid, re
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Paths (change PHOTOS_DIR to any folder on your laptop) ───────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, "player_photos")   # ← photos go here
DATA_FILE  = os.path.join(BASE_DIR, "game_data.json")  # ← scores/players here

os.makedirs(PHOTOS_DIR, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": {}, "scores": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return jsonify(status="ok", message="BlinkRun local server running")


@app.route("/api/register", methods=["POST"])
def register():
    body  = request.get_json(force=True)
    name  = (body.get("name") or "").strip()[:50]
    photo = body.get("photo", "")  # data:image/jpeg;base64,...

    if not name:
        return jsonify(success=False, error="Name is required"), 400

    player_id  = str(uuid.uuid4())
    photo_path = None

    # Save photo to ./player_photos/
    if photo:
        try:
            match = re.match(r"data:(image/\w+);base64,(.+)", photo)
            if match:
                ext       = match.group(1).split("/")[1]    # jpeg / png
                raw_bytes = base64.b64decode(match.group(2))
                filename  = f"{name.replace(' ','_')}_{player_id[:8]}.{ext}"
                full_path = os.path.join(PHOTOS_DIR, filename)
                with open(full_path, "wb") as f:
                    f.write(raw_bytes)
                photo_path = full_path
                print(f"  Photo saved -> {full_path}")
        except Exception as e:
            print(f"  Photo save error: {e}")

    # Save player record
    data = load_data()
    data["players"][player_id] = {
        "id":         player_id,
        "name":       name,
        "photo_path": photo_path,
        "joined_at":  datetime.now().isoformat()
    }
    save_data(data)
    print(f"  Registered: {name}")
    return jsonify(success=True, player_id=player_id, photo_saved_to=photo_path)


@app.route("/api/score", methods=["POST"])
def save_score():
    body      = request.get_json(force=True)
    player_id = body.get("player_id")
    score     = int(body.get("score", 0))

    if not player_id:
        return jsonify(success=False, error="player_id required"), 400

    data   = load_data()
    player = data["players"].get(player_id, {})
    name   = player.get("name", "Unknown")

    data["scores"].append({
        "player_id": player_id,
        "name":      name,
        "score":     score,
        "played_at": datetime.now().isoformat()
    })
    save_data(data)
    print(f"  Score saved: {name} -> {score}")
    return jsonify(success=True)


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    data = load_data()
    best = {}
    for row in data["scores"]:
        n = row["name"]
        if n not in best or row["score"] > best[n]:
            best[n] = row["score"]
    top10 = sorted(
        [{"name": n, "score": s} for n, s in best.items()],
        key=lambda x: x["score"], reverse=True
    )[:10]
    return jsonify(leaderboard=top10)


@app.route("/api/players", methods=["GET"])
def list_players():
    data = load_data()
    return jsonify(players=list(data["players"].values()))


@app.route("/photos/<path:filename>")
def serve_photo(filename):
    """View a saved photo in browser: http://localhost:5000/photos/filename.jpg"""
    return send_from_directory(PHOTOS_DIR, filename)

@app.route("/game")
def game():
    return send_from_directory(BASE_DIR, "index.html")

if __name__ == "__main__":
    print("\n" + "="*52)
    print("  BlinkRun Local Server")
    print("="*52)
    print(f"  Photos folder : {PHOTOS_DIR}")
    print(f"  Data file     : {DATA_FILE}")
    print(f"  Open browser  : http://localhost:5000")
    print("="*52 + "\n")
    app.run(debug=True, port=5000)

    