import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymongo

app = Flask(__name__)
CORS(app)  # Habilita peticiones desde Flutter evitando bloqueos CORS

# Render inyecta la variable de entorno MONGO_URI configurada en el panel
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["shutztv_db"]

# Colecciones
col_tv = db["envivo_tv"]
col_peliculas = db["peliculas"]
col_series = db["series"]

# -------------------------------------------------------------
# ENDPOINTS GET (Consumidos por main.dart en Flutter)
# -------------------------------------------------------------

@app.route('/api/tv', methods=['GET'])
def get_tv():
    try:
        data = list(col_tv.find({}, {"_id": 0}))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/peliculas', methods=['GET'])
def get_peliculas():
    try:
        data = list(col_peliculas.find({}, {"_id": 0}))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/series', methods=['GET'])
def get_series():
    try:
        data = list(col_series.find({}, {"_id": 0}))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------------
# ENDPOINT POST (Consumido por megascraper_completo.py)
# -------------------------------------------------------------

@app.route('/api/sync', methods=['POST'])
def sync_data():
    payload = request.get_json(silent=True) or {}
    
    try:
        # Sincroniza Canales de TV / Noticias / Deportes
        if "envivo_tv" in payload and payload["envivo_tv"]:
            for item in payload["envivo_tv"]:
                col_tv.update_one({"titulo": item["titulo"]}, {"$set": item}, upsert=True)
                
        # Sincroniza Películas
        if "peliculas" in payload and payload["peliculas"]:
            for item in payload["peliculas"]:
                col_peliculas.update_one({"url": item["url"]}, {"$set": item}, upsert=True)
                
        # Sincroniza Series
        if "series" in payload and payload["series"]:
            for item in payload["series"]:
                col_series.update_one({"url": item["url"]}, {"$set": item}, upsert=True)
                
        return jsonify({"status": "ok", "message": "Base de datos sincronizada con éxito"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint de comprobación básica
@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "online", "app": "Shutz TV API"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
