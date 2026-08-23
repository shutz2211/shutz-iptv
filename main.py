import os
import time
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
    print("[+] Ejecutando scraper masivo con anti-bloqueo (modo humano)...")
    
    BASE_URL = "https://cuevana3i.bio"
    
    urls = [f"{BASE_URL}/"]
    urls += [f"{BASE_URL}/peliculas/page/{i}/" for i in range(1, 16)]
    urls += [f"{BASE_URL}/series/page/{i}/" for i in range(1, 6)]
    
    guardadas = 0
    for url in urls:
        try:
            print(f"[*] Visitando: {url}")
            res = requests.get(url, headers=HEADERS, timeout=10)
            
            if res.status_code != 200:
                print(f"[-] Bloqueo o error {res.status_code} en {url}. Saltando página...")
                time.sleep(2) # Pausa incluso si falla
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            all_links = soup.find_all("a")
            
            nuevas_en_pagina = 0
            for a in all_links:
                href = a.get("href", "")
                
                if href and ("/pelicula/" in href or "/serie/" in href or "/episodio/" in href):
                    img_tag = a.find("img")
                    
                    poster = ""
                    if img_tag:
                        poster = (
                            img_tag.get("data-src") or 
                            img_tag.get("src") or 
                            img_tag.get("data-lazy-src") or 
                            img_tag.get("srcset") or ""
                        )
                        if " " in poster:
                            poster = poster.split(" ")[0]
                    
                    title = ""
                    if img_tag and img_tag.get("alt"):
                        title = img_tag.get("alt")
                    elif a.get("title"):
                        title = a.get("title")
                    else:
                        title = a.get_text(strip=True)
                    
                    if href and not href.startswith("http"):
                        href = BASE_URL + href

                    if poster and poster.startswith("//"):
                        poster = "https:" + poster
                        
                    if title and len(title.strip()) > 2:
                        peli = {
                            "title": title.strip(),
                            "url": href,
                            "poster": poster.strip()
                        }
                        
                        res_db = movies_collection.update_one({"url": href}, {"$set": peli}, upsert=True)
                        if res_db.upserted_id:
                            nuevas_en_pagina += 1
                            guardadas += 1
                            
            print(f"[+] {nuevas_en_pagina} nuevas encontradas en esta página.")
            
            # Pausa de 2 segundos antes de pasar a la siguiente página para evitar el baneo
            time.sleep(2)
            
        except Exception as e:
            print(f"[-] Error en {url}: {e}")
            
    print(f"[🎉] Raspado masivo finalizado. Total nuevas guardadas hoy: {guardadas}")

@app.get("/")
def home():
    return {"status": "API Shutz TV Activa"}

@app.get("/scrape-all")
@app.get("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(ejecutar_scraper)
    return {"status": "Escaneo masivo iniciado en segundo plano. Revisar los logs en Render."}

@app.get("/catalog")
def get_catalog():
    movies = list(movies_collection.find({}, {"_id": 0}))
    return movies
