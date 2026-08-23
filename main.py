import os
from fastapi import FastAPI, BackgroundTasks
from pymongo import MongoClient

app = FastAPI()

# Cadena de conexión directa a MongoDB Atlas
MONGO_URI = "mongodb+srv://skinfesttournament_db_user:132123HolaMongo@cluster0.lx60nil.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["shutz_tv_db"]
movies_collection = db["movies"]

# Definimos el endpoint que estabas intentando llamar
@app.get("/scrape-all")
@app.get("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(ejecutar_scraper)
    return {"status": "Escaneo iniciado en segundo plano. La base de datos se irá poblando de a poco."}

@app.get("/catalog")
def get_catalog():
    movies = list(movies_collection.find({}, {"_id": 0}))
    return {"total": len(movies), "movies": movies}

def ejecutar_scraper():
    # Tu función lógica de scraping aquí
    print("[+] Ejecutando raspado e insertando en MongoDB...")
