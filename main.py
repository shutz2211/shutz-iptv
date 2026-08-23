import urllib.parse
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

def extract_real_stream(embed_url: str) -> str | None:
    """Extrae el enlace directo (.m3u8 / .mp4) desde el reproductor con yt-dlp."""
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': HEADERS['User-Agent'],
            'Referer': urllib.parse.urlparse(embed_url).scheme + "://" + urllib.parse.urlparse(embed_url).netloc
        }
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(embed_url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"[-] yt-dlp fallo en {embed_url}: {e}")
        return None

def resolve_cuevana_stream(movie_url: str) -> str | None:
    """Entra a la ficha de Cuevana y extrae los reproductores/iFrames."""
    try:
        res = requests.get(movie_url, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # Buscar iFrames o data-src de reproductores dentro de la página
        for iframe in soup.find_all(['iframe', 'a']):
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('href')
            if not src:
                continue

            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = f"https://cuevana3i.bio{src}"

            # Filtrar enlaces irrelevantes
            if any(domain in src for domain in ['facebook', 'twitter', 'whatsapp', 'telegram', 'cuevana3i.bio']):
                continue

            stream = extract_real_stream(src)
            if stream:
                return stream

        return None
    except Exception as e:
        print(f"[-] Error en película {movie_url}: {e}")
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

        # Selectores específicos del tema WordPress / Cuevana
        items = soup.select('ul.Posters li, .TItem, .item, article.item-movies')

        for item in items[:8]:  # Límite para responder rápido en Render
            title_el = item.select_one('.Title, .title, h2, h3, .entry-title')
            img_el = item.select_one('img')
            link_el = item.select_one('a')

            if title_el and link_el:
                title = title_el.get_text(strip=True)
                
                poster = ''
                if img_el:
                    poster = img_el.get('src') or img_el.get('data-src') or img_el.get('srcset') or ''
                    if ' ' in poster:  # Si viene con srcset agarra la primera URL
                        poster = poster.split(' ')[0]
                    if poster.startswith('//'):
                        poster = f"https:{poster}"
                    elif poster.startswith('/'):
                        poster = f"{BASE_URL}{poster}"

                movie_link = link_el.get('href') or ''
                if movie_link.startswith('/'):
                    movie_link = f"{BASE_URL}{movie_link}"

                stream_url = None
                if movie_link:
                    stream_url = resolve_cuevana_stream(movie_link)

                # Fallback al video de prueba si un reproductor específico falla
                if not stream_url:
                    stream_url = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"

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
        },
        {
            "title": "Sintel (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/Sintel_poster.jpg",
            "stream_url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
            "headers": {"User-Agent": HEADERS["User-Agent"]}
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
