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

def ejecutar_scraper():
    print("[+] Iniciando raspado de Cuevana...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    BASE_URL = "https://cuevana3i.bio"
    
    # Probamos la portada y las secciones principales
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/estrenos/",
        f"{BASE_URL}/peliculas/"
    ]
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"[-] Error HTTP {res.status_code} en {url}")
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Selector universal: busca cualquier enlace que contenga una imagen dentro
            links = soup.find_all("a")
            
            peli_count = 0
            for a in links:
                href = a.get("href", "")
                img_tag = a.find("img")
                
                # Si tiene link, imagen y parece una película/serie
                if href and img_tag:
                    title = a.get_text(strip=True) or img_tag.get("alt", "") or a.get("title", "")
                    img_src = img_tag.get("data-src") or img_tag.get("src") or img_tag.get("data-lazy-src") or ""
                    
                    if len(title) > 2 and img_src:
                        if not href.startswith("http"):
                            href = BASE_URL + href
                            
                        peli = {
                            "title": title,
                            "url": href,
                            "poster": img_src
                        }
                        
                        # Guarda o actualiza en MongoDB
                        movies_collection.update_one({"url": href}, {"$set": peli}, upsert=True)
                        peli_count += 1
                        
            print(f"[+] Éxito en {url}: Se guardaron {peli_count} ítems.")
        except Exception as e:
            print(f"[-] Error procesando {url}: {e}")

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
    movies = list(movies_collection.find({}, {"_id": 0}))
    return {"total": len(movies), "movies": movies}
