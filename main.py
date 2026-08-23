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
    print("[+] Limpiando colección y ejecutando scraper flexible...")
    movies_collection.delete_many({}) # Limpiamos la base
    
    BASE_URL = "https://cuevana3i.bio"
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/peliculas/",
        f"{BASE_URL}/estrenos/",
        f"{BASE_URL}/series/"
    ]
    
    guardadas = 0
    for url in urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"[-] Status {res.status_code} en {url}")
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Buscamos TODOS los enlaces de la página
            all_links = soup.find_all("a")
            
            for a in all_links:
                href = a.get("href", "")
                
                # Filtramos para asegurarnos de que sea una ficha de película o serie
                if href and ("/pelicula/" in href or "/serie/" in href or "/episodio/" in href):
                    img_tag = a.find("img")
                    
                    # Intentamos obtener la imagen de cualquier atributo posible
                    poster = ""
                    if img_tag:
                        poster = (
                            img_tag.get("data-src") or 
                            img_tag.get("src") or 
                            img_tag.get("data-lazy-src") or 
                            img_tag.get("srcset") or ""
                        )
                        # Si viene un srcset, nos quedamos con la primera URL
                        if " " in poster:
                            poster = poster.split(" ")[0]
                    
                    # Obtenemos el título de la película
                    title = ""
                    if img_tag and img_tag.get("alt"):
                        title = img_tag.get("alt")
                    elif a.get("title"):
                        title = a.get("title")
                    else:
                        title = a.get_text(strip=True)
                    
                    # Normalizamos la URL si es relativa
                    if href and not href.startswith("http"):
                        href = BASE_URL + href

                    # Si el poster viene relativo (ej: //imagen.jpg)
                    if poster and poster.startswith("//"):
                        poster = "https:" + poster
                        
                    # Si tenemos título y URL válida, guardamos
                    if title and len(title.strip()) > 2:
                        peli = {
                            "title": title.strip(),
                            "url": href,
                            "poster": poster.strip()
                        }
                        
                        # upsert evita duplicados por URL
                        res_db = movies_collection.update_one({"url": href}, {"$set": peli}, upsert=True)
                        if res_db.upserted_id:
                            guardadas += 1
                            
            print(f"[+] Éxito en {url}. Películas procesadas hasta ahora.")
        except Exception as e:
            print(f"[-] Error en {url}: {e}")
            
    print(f"[🎉] Raspado finalizado con éxito. Nuevas guardadas: {guardadas}")

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
    return movies
