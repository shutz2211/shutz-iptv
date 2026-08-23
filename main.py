import urllib.parse
import urllib3
import time
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

CACHE_CATALOG = []
LAST_SCRAPE_TIME = 0
CACHE_DURATION = 86400  # Se actualiza una vez al día (24 hrs) porque es un raspado masivo

def scrape_cuevana_entire_site(max_pages=None):
    """
    Si max_pages es None, recorre INFINITAMENTE todas las páginas del sitio
    hasta que no existan más películas o la web dé 404.
    """
    all_movies = []
    seen_titles = set()
    page = 1
    
    print("[+] Iniciando recorrido COMPLETO e ilimitado de cuevana3i.bio...")

    while True:
        # Freno de seguridad manual opcional
        if max_pages and page > max_pages:
            print(f"[*] Se alcanzó el límite configurado de {max_pages} páginas.")
            break

        url = "https://cuevana3i.bio/peliculas" if page == 1 else f"https://cuevana3i.bio/peliculas/page/{page}/"

        try:
            res = requests.get(url, headers=HEADERS, timeout=10, verify=False)

            # Si el sitio responde 404 significa que superamos la última página real
            if res.status_code != 200:
                print(f"[*] Fin definitivo del catálogo alcanzado en la página {page}. HTTP {res.status_code}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')

            # Selectores de tarjetas en Cuevana 3
            items = soup.select('li.TItem, ul.MovieList li, article.Posters-item, div.Posters-item, article.item, .post')

            if not items:
                print(f"[*] No hay más contenido en la página {page}. Fin del sitio.")
                break

            movies_found_in_page = 0

            for item in items:
                img_el = item.find('img')
                if not img_el:
                    continue

                title = img_el.get('alt') or img_el.get('title') or ''
                title = title.strip()

                poster = img_el.get('data-src') or img_el.get('src') or ''

                if poster.startswith('//'):
                    poster = 'https:' + poster

                if title and poster and title not in seen_titles:
                    seen_titles.add(title)
                    clean_title = urllib.parse.quote(title)

                    stream_url = f"https://vidsrc.cc/v2/embed/movie?title={clean_title}"

                    all_movies.append({
                        "title": title,
                        "type": "movie",
                        "poster": poster,
                        "stream_url": stream_url
                    })
                    movies_found_in_page += 1

            print(f"[+] Página {page} extraída con éxito. (+{movies_found_in_page} películas)")

            # Si una página no sumó ningún elemento nuevo, cortamos el bucle
            if movies_found_in_page == 0:
                print(f"[*] No se detectaron películas nuevas en la página {page}. Finalizando...")
                break

            page += 1
            time.sleep(0.2)  # Pausa breve para evitar saturar el servidor

        except Exception as e:
            print(f"[-] Error inesperado en página {page}: {e}")
            break

    print(f"[✔] Recorrido 100% finalizado. Total de películas obtenidas: {len(all_movies)}")
    return all_movies


@app.get("/catalog")
def get_catalog(force_refresh: bool = False):
    global CACHE_CATALOG, LAST_SCRAPE_TIME
    
    current_time = time.time()

    if not CACHE_CATALOG or (current_time - LAST_SCRAPE_TIME > CACHE_DURATION) or force_refresh:
        # Pasar max_pages=None para recorrer la web ENTERA
        scraped_data = scrape_cuevana_entire_site(max_pages=None)
        
        if scraped_data:
            CACHE_CATALOG = scraped_data
            LAST_SCRAPE_TIME = current_time

    return CACHE_CATALOG

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
