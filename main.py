import re
import urllib.parse
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

def get_cuevana_movie_data(movie_url: str):
    """Extrae el ID de la película (o slug) y busca opciones de reproducción válidas."""
    try:
        res = requests.get(movie_url, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # Buscar iFrames incrustados en la página
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src') or iframe.get('data-src') or ''
            if not src:
                continue
            
            if src.startswith('//'):
                src = 'https:' + src

            # Ignorar widgets sociales
            if any(x in src for x in ['facebook', 'twitter', 'telegram', 'whatsapp']):
                continue

            # Si encontramos un reproductor externo
            if 'http' in src:
                return src

        # Si no hay iframe simple, intentar obtener el ID de IMDb si está disponible
        imdb_match = re.search(r'tt\d{7,8}', res.text)
        if imdb_match:
            imdb_id = imdb_match.group(0)
            return f"https://vidsrc.cc/v2/embed/movie/{imdb_id}"

        return None
    except Exception as e:
        print(f"[-] Error resolviendo película {movie_url}: {e}")
        return None

@app.get("/catalog")
def get_catalog():
    BASE_URL = "https://cuevana3i.bio"
    try:
        response = requests.get(f"{BASE_URL}/inicio-2/", headers=HEADERS, timeout=8)
        if response.status_code != 200:
            response = requests.get(BASE_URL, headers=HEADERS, timeout=8)

        if response.status_code != 200:
            return get_fallback_catalog()

        soup = BeautifulSoup(response.text, 'html.parser')
        catalog = []

        # Buscar los items en el catálogo
        items = soup.select('ul.Posters li, .TItem, .item, article.item-movies')

        for item in items:
            title_el = item.select_one('.Title, .title, h2, h3, .entry-title')
            img_el = item.select_one('img')
            link_el = item.select_one('a')

            if title_el and link_el:
                title = title_el.get_text(strip=True)
                if not title:
                    continue

                poster = ''
                if img_el:
                    poster = img_el.get('src') or img_el.get('data-src') or ''
                    if not poster and img_el.get('srcset'):
                        poster = img_el.get('srcset').split(' ')[0]
                    
                    if poster.startswith('//'):
                        poster = f"https:{poster}"
                    elif poster.startswith('/'):
                        poster = f"{BASE_URL}{poster}"

                movie_link = link_el.get('href') or ''
                if movie_link.startswith('/'):
                    movie_link = f"{BASE_URL}{movie_link}"

                stream_url = None
                if movie_link:
                    stream_url = get_cuevana_movie_data(movie_link)

                # Si no logra resolver un reproductor único, genera un embed de respaldo por búsqueda
                if not stream_url and movie_link:
                    clean_title = urllib.parse.quote(title)
                    stream_url = f"https://vidsrc.cc/v2/embed/movie?title={clean_title}"

                catalog.append({
                    "title": title,
                    "type": "movie",
                    "poster": poster,
                    "stream_url": stream_url,
                    "headers": {
                        "User-Agent": HEADERS["User-Agent"],
                        "Referer": BASE_URL
                    }
                })

                # Traer hasta 20 películas para cargar rápido
                if len(catalog) >= 20:
                    break

        return catalog if catalog else get_fallback_catalog()

    except Exception as e:
        print(f"Error raspando Cuevana: {e}")
        return get_fallback_catalog()

def get_fallback_catalog():
    return [
        {
            "title": "Big Buck Bunny (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg",
            "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            "headers": {"User-Agent": HEADERS["User-Agent"]}
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
