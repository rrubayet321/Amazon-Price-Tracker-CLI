"""Scrape AFI's top movies and write them to movies.txt."""

from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.afi.com/afis-100-years-100-movies/"
HEADERS = {
    # Pretend to be a desktop Chrome browser to avoid simple blocks.
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def fetch_top_movies(url: str = URL, limit: int = 100) -> list[str]:
    """Return a list of movie titles from the AFI page, trimmed to *limit*."""

    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    titles = [tag.get_text(strip=True) for tag in soup.select("h6.q_title")]
    return titles[:limit] if limit else titles


def save_movies(movies: list[str], path: Path | str = "movies.txt") -> Path:
    """Write movie titles to disk (one per line) and return the path."""

    output_path = Path(path)
    output_path.write_text("\n".join(movies) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    movies = fetch_top_movies()
    output_path = save_movies(movies)
    print(f"Wrote {len(movies)} titles to {output_path}")


if __name__ == "__main__":
    main()
