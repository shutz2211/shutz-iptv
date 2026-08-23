import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = "mongodb+srv://skinfesttournament_db_user:132123HolaMongo@cluster0.lx60nil.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["shutz_tv_db"]
movies_collection = db["movies"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

def ejecutar_scraper():
    print("[+] Limpiando base de datos y comenzando raspado real...")
    # Borramos los registros viejos/rotos para empezar limpios
    movies_collection.delete_many({})
    
    BASE_URL = "https://cuevana3i.bio"
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/peliculas/",
        f"{BASE_URL}/estrenos/"
    ]
    
    guardadas = 0
    for url in urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Buscamos los contenedores de películas de Cuevana
            items = soup.select(".Posters li, article.item, .TPost li, .item-peli")
            
            for item in items:
                link_tag = item.find("a")
                img_tag = item.find("img")
                
                if link_tag and img_tag:
                    href = link_tag.get("href", "")
                    title = img_tag.get("alt", "") or link_tag.get("title", "") or item.get_text(strip=True)
                    poster = img_tag.get("data-src") or img_tag.get("src") or img_tag.get("data-lazy-src") or ""
                    
                    # Validaciones estrictas: debe tener título, imagen y URL de película
                    if title and poster and ("http" in poster or "//" in poster) and len(title) > 2:
                        if not href.startswith("http"):
                            href = BASE_URL + href
                            
                        peli = {
                            "title": title,
                            "url": href,
                            "poster": poster
                        }
                        
                        movies_collection.update_one({"url": href}, {"$set": peli}, upsert=True)
                        guardadas += 1
                        
        except Exception as e:
            print(f"[-] Error en {url}: {e}")
            
    print(f"[🎉] Proceso terminado. Se guardaron {guardadas} películas reales.")

@app.get("/")
def home():
    return {"status": "API Shutz TV Activa"}

@app.get("/scrape-all")
@app.get("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(ejecutar_scraper)
    return {"status": "Escaneo iniciado en segundo plano."}

@app.get("/catalog")
def get_catalog():
    # Devuelve solo las películas que tengan título y afiche válido
    movies = list(movies_collection.find({"poster": {"$ne": ""}, "title": {"$ne": ""}}, {"_id": 0}))
    return movies
