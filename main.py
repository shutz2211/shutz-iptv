from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_real_stream(embed_url: str) -> str | None:
    """Intenta extraer la URL directa de video (.m3u8 / .mp4) usando yt-dlp."""
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(embed_url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"Error extrayendo stream con yt-dlp de {embed_url}: {e}")
        return None

@app.get("/catalog")
def get_catalog():
    """Rasca películas/series de vidsrc.to y extrae streams reales."""
    try:
        url = "https://vidsrc.to"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return get_fallback_catalog()

        soup = BeautifulSoup(response.text, 'html.parser')
        catalog = []
        items = soup.select('.card, .item, .movie-item')

        for item in items[:10]:  # Límite a 10 para evitar sobrecargar la extracción
            title_el = item.select_one('.title, h2, h3, .name')
            img_el = item.select_one('img')
            link_el = item.select_one('a')

            if title_el and img_el:
                title = title_el.get_text(strip=True)
                poster = img_el.get('src') or img_el.get('data-src') or ''
                
                if poster.startswith('/'):
                    poster = f"https://vidsrc.to{poster}"

                # Intentamos obtener la URL de detalle o embed
                item_url = link_el.get('href') if link_el else None
                if item_url and item_url.startswith('/'):
                    item_url = f"https://vidsrc.to{item_url}"

                # Extraemos la URL real de transmisión
                stream_url = None
                if item_url:
                    stream_url = extract_real_stream(item_url)

                # Si no se pudo resolver el stream directo, se asigna un fallback para que no rompa la app
                if not stream_url:
                    stream_url = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"

                catalog.append({
                    "title": title,
                    "type": "movie",
                    "poster": poster,
                    "stream_url": stream_url,
                    "headers": {
                        "User-Agent": HEADERS["User-Agent"],
                        "Referer": url
                    }
                })

        return catalog if catalog else get_fallback_catalog()

    except Exception as e:
        print(f"Error en scraping: {e}")
        return get_fallback_catalog()


def get_fallback_catalog():
    return [
        {
            "title": "Big Buck Bunny (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg",
            "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            "headers": {"User-Agent": "Mozilla/5.0"}
        },
        {
            "title": "Sintel (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/Sintel_poster.jpg",
            "stream_url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
            "headers": {"User-Agent": "Mozilla/5.0"}
        }
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
