import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, BackgroundTasks
from pymongo import MongoClient

app = FastAPI()

# Conexión a MongoDB Atlas
MONGO_URI = "mongodb+srv://skinfesttournament_db_user:132123HolaMongo@cluster0.lx60nil.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["shutz_tv_db"]
movies_collection = db["movies"]

# --- FUNCION DEL SCRAPER ---
def ejecutar_scraper():
    print("[+] Iniciando raspado de Cuevana...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    BASE_URL = "https://cuevana3i.bio"
    
    for page in range(1, 6):
        url = f"{BASE_URL}/peliculas/page/{page}/"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"[-] Status {res.status_code} en página {page}")
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            items = soup.select("ul.Posters li, article.item, .TPost li")
            
            peli_list = []
            for item in items:
                title_elem = item.select_one(".Title, h2, .entry-title")
                link_elem = item.select_one("a")
                img_elem = item.select_one("img")
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get("href", "")
                    img = img_elem.get("data-src") or img_elem.get("src", "") if img_elem else ""
                    
                    if link and not link.startswith("http"):
                        link = BASE_URL + link
                        
                    peli = {
                        "title": title,
                        "url": link,
                        "poster": img
                    }
                    
                    movies_collection.update_one({"url": link}, {"$set": peli}, upsert=True)
                    peli_list.append(peli)
                    
            print(f"[+] Página {page} procesada (+{len(peli_list)} películas).")
        except Exception as e:
            print(f"[-] Error en página {page}: {e}")

# --- RUTAS DE LA API ---

@app.get("/")
def home():
    return {"status": "API Shutz TV Activa"}

@app.get("/scrape-all")
@app.get("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(ejecutar_scraper)
    return {"status": "Escaneo iniciado en segundo plano. La base de datos se irá poblando."}

@app.get("/catalog")
def get_catalog():
    movies = list(movies_collection.find({}, {"_id": 0}))
    return {"total": len(movies), "movies": movies}
