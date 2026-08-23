import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymongo

app = Flask(__name__)
CORS(app)  # Permite peticiones desde Flutter sin bloqueos CORS

# Render pasa la URI de MongoDB por Variables de Entorno o usa fallback local
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["shutztv_db"]

# -------------------------------------------------------------
# ENDPOINTS GET (Para que tu Flutter consuma en main.dart)
# -------------------------------------------------------------
@app.route('/api/tv', methods=['GET'])
def get_tv():
    datos = list(db["envivo_tv"].find({}, {"_id": 0}))
    return jsonify(datos), 200

@app.route('/api/peliculas', methods=['GET'])
def get_peliculas():
    datos = list(db["peliculas"].find({}, {"_id": 0}))
    return jsonify(datos), 200

@app.route('/api/series', methods=['GET'])
def get_series():
    datos = list(db["series"].find({}, {"_id": 0}))
    return jsonify(datos), 200

# -------------------------------------------------------------
# ENDPOINT POST (Para que tu megascraper local suba los datos)
# -------------------------------------------------------------
@app.route('/api/sync', methods=['POST'])
def sync_data():
    payload = request.get_json(silent=True) or {}
    
    if "envivo_tv" in payload:
        for item in payload["envivo_tv"]:
            db["envivo_tv"].update_one({"titulo": item["titulo"]}, {"$set": item}, upsert=True)
            
    if "peliculas" in payload:
        for item in payload["peliculas"]:
            db["peliculas"].update_one({"url": item["url"]}, {"$set": item}, upsert=True)
            
    if "series" in payload:
        for item in payload["series"]:
            db["series"].update_one({"url": item["url"]}, {"$set": item}, upsert=True)
            
    return jsonify({"status": "ok", "message": "Sincronización exitosa"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
