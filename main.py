from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HN_URL = "https://news.ycombinator.com/news"


def fetch_front_page(url: str = HN_URL) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def parse_articles(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for row in soup.find_all("tr", class_="athing"):
        title_span = row.find("span", class_="titleline")
        if not title_span:
            continue

        link_tag = title_span.find("a")
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        link = urljoin(HN_URL, link_tag.get("href", ""))

        subtext = row.find_next_sibling("tr")
        score_tag = subtext.find("span", class_="score") if subtext else None
        points = int(score_tag.get_text().split()[0]) if score_tag else 0

        articles.append(
            {
                "title": title,
                "link": link,
                "points": points,
            }
        )

    return articles


def find_top_story(articles: list[dict[str, object]]) -> dict[str, object] | None:
    if not articles:
        return None

    return max(articles, key=lambda item: item["points"])


def main() -> None:
    try:
        page_html = fetch_front_page()
    except requests.RequestException as exc:
        print(f"Failed to load {HN_URL}: {exc}")
        return

    articles = parse_articles(page_html)
    top_story = find_top_story(articles)

    if not top_story:
        print("No stories found on Hacker News.")
        return

    print("Today's highest-voted Hacker News story:")
    print(f"Title: {top_story['title']}")
    print(f"Link: {top_story['link']}")
    print(f"Points: {top_story['points']}")


if __name__ == "__main__":
    main()
