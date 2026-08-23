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
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

def fetch_popular_movies():
    """
    Obtiene las películas populares raspando la sección de tendencias de JustWatch Argentina/España.
    """
    url = "https://www.justwatch.com/es/peliculas"
    movies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscamos las tarjetas de películas en el HTML
            items = soup.select('.title-list-row__column-header, .picture-comp, a.title-list-grid__item--link')
            
            for item in items:
                img_el = item.select_one('img')
                if not img_el:
                    continue

                title = img_el.get('alt') or ''
                poster = img_el.get('src') or img_el.get('data-src') or ''

                if title and poster and not poster.endswith('.svg'):
                    # Si la imagen es relativa la completamos
                    if poster.startswith('//'):
                        poster = f"https:{poster}"
                    
                    # Generamos la URL de reproducción embedding por nombre de título
                    clean_title = urllib.parse.quote(title)
                    stream_url = f"https://vidsrc.cc/v2/embed/movie?title={clean_title}"

                    movies.append({
                        "title": title,
                        "type": "movie",
                        "poster": poster,
                        "stream_url": stream_url,
                        "headers": {"User-Agent": HEADERS["User-Agent"]}
                    })

                if len(movies) >= 18:
                    break
    except Exception as e:
        print(f"[-] Error en JustWatch scraper: {e}")

    return movies

@app.get("/catalog")
def get_catalog():
    # 1. Intentamos obtener las películas
    catalog = fetch_popular_movies()

    # 2. Si JustWatch bloquea por User-Agent, usamos un catálogo estático amplio de estrenos reales
    if not catalog:
        catalog = [
            {
                "title": "Dune: Parte Dos",
                "type": "movie",
                "poster": "https://image.tmdb.org/t/p/w500/8b8R8A88Mje929xR2T358s9T3S1.jpg",
                "stream_url": "https://vidsrc.cc/v2/embed/movie/693134",
                "headers": {"User-Agent": HEADERS["User-Agent"]}
            },
            {
                "title": "Deadpool & Wolverine",
                "type": "movie",
                "poster": "https://image.tmdb.org/t/p/w500/8cdWjvZ21I3L3i4S3f4f31i3.jpg",
                "stream_url": "https://vidsrc.cc/v2/embed/movie/533535",
                "headers": {"User-Agent": HEADERS["User-Agent"]}
            },
            {
                "title": "Oppenheimer",
                "type": "movie",
                "poster": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
                "stream_url": "https://vidsrc.cc/v2/embed/movie/872585",
                "headers": {"User-Agent": HEADERS["User-Agent"]}
            },
            {
                "title": "Spider-Man: Across the Spider-Verse",
                "type": "movie",
                "poster": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5XjR3eL8.jpg",
                "stream_url": "https://vidsrc.cc/v2/embed/movie/569094",
                "headers": {"User-Agent": HEADERS["User-Agent"]}
            },
            {
                "title": "Avatar: El Camino del Agua",
                "type": "movie",
                "poster": "https://image.tmdb.org/t/p/w500/t68241L139c23315a63914a82.jpg",
                "stream_url": "https://vidsrc.cc/v2/embed/movie/76600",
                "headers": {"User-Agent": HEADERS["User-Agent"]}
            }
        ]

    return catalog

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
