import urllib.parse
import time
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

# Cache global en memoria para guardar las películas scrapeadas de toda la web
CACHE_CATALOG = []
LAST_SCRAPE_TIME = 0
CACHE_DURATION = 3600  # Vuelve a recorrer el sitio completo cada 1 hora (3600 seg)

def scrape_entire_website(max_pages=20):
    """
    Recorre el sitio página por página hasta que no haya más contenido 
    o alcance el límite de seguridad (max_pages).
    """
    all_movies = []
    seen_titles = set()
    page = 1
    
    print("[+] Iniciando recorrido completo del sitio web...")

    while page <= max_pages:
        # La estructura típica de paginación
        url = f"https://www.cinecalidad.ms/page/{page}/" if page > 1 else "https://www.cinecalidad.ms/"
        
        try:
            res = requests.get(url, headers=HEADERS, timeout=6)
            
            # Si la página da 404 o falla, llegamos al final del sitio
            if res.status_code != 200:
                print(f"[*] Fin del sitio alcanzado en la página {page}. HTTP: {res.status_code}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Seleccionamos las tarjetas de películas (ajustar selector según el sitio)
            items = soup.select('article.item, div.home-pelikulas div.item, .poster')
            
            # Si no hay más películas en esta página, detenemos el recorrido
            if not items:
                print(f"[*] No se encontraron más películas en la página {page}. Finalizando recorrido.")
                break

            movies_found_in_page = 0

            for item in items:
                img_el = item.find('img')
                link_el = item.find('a')
                
                if not img_el:
                    continue

                title = img_el.get('alt') or img_el.get('title') or ''
                title = title.strip()
                poster = img_el.get('src') or img_el.get('data-src') or ''

                if title and poster and title not in seen_titles:
                    seen_titles.add(title)
                    clean_title = urllib.parse.quote(title)
                    
                    # Estructura del reproductor reproduciendo el título
                    stream_url = f"https://vidsrc.cc/v2/embed/movie?title={clean_title}"

                    all_movies.append({
                        "title": title,
                        "type": "movie",
                        "poster": poster,
                        "stream_url": stream_url,
                        "headers": {"User-Agent": HEADERS["User-Agent"]}
                    })
                    movies_found_in_page += 1

            print(f"[+] Página {page} procesada exitosamente. Películas añadidas: {movies_found_in_page}")
            
            # Si una página no sumó películas nuevas, cortar para evitar bucles infinitos
            if movies_found_in_page == 0:
                break

            page += 1
            time.sleep(0.3)  # Pequeña pausa para no saturar ni ser bloqueados

        except Exception as e:
            print(f"[-] Error raspando la página {page}: {e}")
            break

    print(f"[✔] Recorrido finalizado. Total de películas obtenidas: {len(all_movies)}")
    return all_movies


@app.get("/catalog")
def get_catalog(force_refresh: bool = False):
    global CACHE_CATALOG, LAST_SCRAPE_TIME
    
    current_time = time.time()
    
    # Si el catálogo está vacío o el caché ya venció (pasó más de 1 hora), escanea todo de nuevo
    if not CACHE_CATALOG or (current_time - LAST_SCRAPE_TIME > CACHE_DURATION) or force_refresh:
        scraped_data = scrape_entire_website(max_pages=50) # Cambiá 50 por la cantidad límite de páginas a recorrer
        
        if scraped_data:
            CACHE_CATALOG = scraped_data
            LAST_SCRAPE_TIME = current_time

    return CACHE_CATALOG

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
