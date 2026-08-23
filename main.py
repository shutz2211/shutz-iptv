import os
import re
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNCIÓN PARA EXTRAER EL ENLACE M3U8 / MP4 FINAL ---
def obtener_stream_m3u8(url_pelicula):
    try:
        res = requests.get(url_pelicula, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. Buscar si hay streams M3U8 directos en el HTML o scripts
        m3u8_matches = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', res.text)
        if m3u8_matches:
            return m3u8_matches[0]

        # 2. Buscar enlaces de embed / IFrames de reproductores
        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src") or iframe.get("data-src") or ""
            if src:
                if not src.startswith("http"):
                    src = "https:" + src if src.startswith("//") else src
                
                # Intentar resolver el iframe
                try:
                    res_iframe = requests.get(src, headers=HEADERS, timeout=5)
                    m3u8_inside = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', res_iframe.text)
                    if m3u8_inside:
                        return m3u8_inside[0]
                except:
                    continue
                    
        return None
    except Exception as e:
        print(f"Error resolviendo m3u8: {e}")
        return None

# --- SCRAPER PRINCIPAL ---
def ejecutar_scraper():
    print("[+] Iniciando raspado de Cuevana...")
    BASE_URL = "https://cuevana3i.bio"
    
    urls = [f"{BASE_URL}/"]
    urls += [f"{BASE_URL}/peliculas/page/{i}/" for i in range(1, 10)]
    
    total_nuevas = 0
    
    for url in urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            links = soup.find_all("a")
            
            for a in links:
                href = a.get("href", "")
                img_tag = a.find("img")
                
                if href and img_tag:
                    title = a.get_text(strip=True) or img_tag.get("alt", "") or a.get("title", "")
                    img_src = img_tag.get("data-src") or img_tag.get("src") or img_tag.get("data-lazy-src") or ""
                    
                    if len(title) > 2 and img_src and ("/pelicula/" in href or "/serie/" in href):
                        if not href.startswith("http"):
                            href = BASE_URL + href
                            
                        peli = {
                            "title": title,
                            "url": href,
                            "poster": img_src
                        }
                        
                        result = movies_collection.update_one({"url": href}, {"$set": peli}, upsert=True)
                        if result.upserted_id:
                            total_nuevas += 1
                        
        except Exception as e:
            print(f"[-] Error en {url}: {e}")
            
    print(f"[🎉] Escaneo completado. Nuevas: {total_nuevas}")

# --- RUTAS DE LA API ---

@app.get("/")
def home():
    return {"status": "API Shutz TV Activa"}

@app.get("/scrape-all")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(ejecutar_scraper)
    return {"status": "Escaneo iniciado en segundo plano."}

@app.get("/catalog")
def get_catalog():
    movies = list(movies_collection.find({}, {"_id": 0}))
    return {"total": len(movies), "movies": movies}

# NUEVA RUTA: Recibe la URL de la película y devuelve el M3U8 directo
@app.get("/get-stream")
def get_stream(movie_url: str):
    stream_url = obtener_stream_m3u8(movie_url)
    if stream_url:
        return {"status": "success", "m3u8": stream_url}
    else:
        return {"status": "error", "message": "No se pudo extraer el stream m3u8 directamente. El reproductor requiere evaluación JS."}
