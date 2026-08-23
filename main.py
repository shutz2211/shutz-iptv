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
    
    # Probamos tanto la portada como la paginación estándar
    urls_to_scrape = [f"{BASE_URL}/"] + [f"{BASE_URL}/inicio/page/{i}/" for i in range(1, 6)]
    
    for url in urls_to_scrape:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"[-] Status {res.status_code} en {url}")
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            # Selectores amplios para capturar los contenedores de Cuevana
            items = soup.select("ul.Posters li, article.item, .TPost li, div.Posters a, .item-peli")
            
            peli_list = []
            for item in items:
                title_elem = item.select_one(".Title, h2, h3, .entry-title, .title")
                link_elem = item if item.name == "a" else item.select_one("a")
                img_elem = item.select_one("img")
                
                if link_elem:
                    title = title_elem.get_text(strip=True) if title_elem else item.get("title", "")
                    link = link_elem.get("href", "")
                    img = ""
                    if img_elem:
                        img = img_elem.get("data-src") or img_elem.get("src") or img_elem.get("data-lazy-src") or ""
                    
                    if title and link:
                        if not link.startswith("http"):
                            link = BASE_URL + link
                            
                        peli = {
                            "title": title,
                            "url": link,
                            "poster": img
                        }
                        
                        movies_collection.update_one({"url": link}, {"$set": peli}, upsert=True)
                        peli_list.append(peli)
                        
            print(f"[+] Procesado {url} (+{len(peli_list)} películas).")
        except Exception as e:
            print(f"[-] Error en {url}: {e}")
