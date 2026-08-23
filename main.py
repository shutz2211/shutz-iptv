from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import urllib.parse

app = FastAPI()

# Permitir conexiones desde Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

def extract_real_stream(embed_url: str) -> str | None:
    """
    Extrae el enlace directo (.m3u8 o .mp4) usando yt-dlp simulando 
    las cabeceras correctas para evitar bloqueos por 403 Forbidden.
    """
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
        print(f"[-] yt-dlp no pudo resolver {embed_url}: {e}")
        return None


def resolve_player_iframes(page_url: str) -> str | None:
    """
    Navega a la página de la película, escanea todos los iFrames 
    y busca un servidor de streaming que yt-dlp pueda parsear.
    """
    try:
        req_headers = HEADERS.copy()
        req_headers["Referer"] = page_url
        res = requests.get(page_url, headers=req_headers, timeout=8)
        
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Buscar iFrames directos en el DOM
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src') or iframe.get('data-src')
            if not src:
                continue

            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                parsed_base = urllib.parse.urlparse(page_url)
                src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"

            # Intentamos extraer el stream desde la URL del iframe
            stream = extract_real_stream(src)
            if stream:
                return stream

        # 2. Si no hay iFrames directos, intentar pasar la URL principal directamente a yt-dlp
        return extract_real_stream(page_url)

    except Exception as e:
        print(f"[-] Error analizando la página {page_url}: {e}")
        return None


@app.get("/catalog")
def get_catalog():
    """Obtiene el catálogo de películas más recientes y extrae sus retransmisiones."""
    BASE_URL = "https://vidsrc.to"
    try:
        response = requests.get(f"{BASE_URL}/embed/movie", headers=HEADERS, timeout=8)
        
        if response.status_code != 200:
            return get_fallback_catalog()

        soup = BeautifulSoup(response.text, 'html.parser')
        catalog = []
        
        # Selectores adaptados a sitios estilo vidsrc / cuevana
        items = soup.select('.card, .item, .movie-item, .film-detail')

        for item in items[:8]:  # Procesamos hasta 8 items para mantener el tiempo de respuesta bajo en Render
            title_el = item.select_one('.title, h2, h3, .name, .film-name')
            img_el = item.select_one('img')
            link_el = item.select_one('a')

            if title_el:
                title = title_el.get_text(strip=True)
                poster = ''
                if img_el:
                    poster = img_el.get('src') or img_el.get('data-src') or ''
                    if poster.startswith('/'):
                        poster = f"{BASE_URL}{poster}"

                # Obtener enlace de la película
                movie_link = link_el.get('href') if link_el else None
                if movie_link and movie_link.startswith('/'):
                    movie_link = f"{BASE_URL}{movie_link}"

                stream_url = None
                if movie_link:
                    stream_url = resolve_player_iframes(movie_link)

                # Si no logra extraer el stream en vivo, se usa el demo HLS para evitar romper el player
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
        print(f"Error en catálogo: {e}")
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
