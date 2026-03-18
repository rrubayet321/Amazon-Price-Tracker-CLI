"""Amazon Price Tracker CLI.

Track one or many Amazon products, store history, and trigger email alerts.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

DEFAULT_TARGET_PRICE = float(os.getenv("TARGET_PRICE", "0"))
DEFAULT_DROP_ALERT_PERCENT = float(os.getenv("DROP_ALERT_PERCENT", "0"))
DEFAULT_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.csv")
SMTP_ADDRESS = os.getenv("SMTP_ADDRESS", "smtp.gmail.com")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

DESKTOP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15A372 Safari/604.1"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
COOKIES = {"i18n-prefs": "USD", "lc-main": "en_US"}


@dataclass
class PriceResult:
    url: str
    name: str
    price: float
    asin: str | None
    previous_price: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track Amazon prices with history and optional email alerts."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Amazon product URL. If omitted, you'll be prompted.",
    )
    parser.add_argument(
        "--urls-file",
        default=None,
        help="Path to a text file with one Amazon URL per line.",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=DEFAULT_TARGET_PRICE,
        help="Alert when price drops below this value (0 disables).",
    )
    parser.add_argument(
        "--drop-alert",
        type=float,
        default=DEFAULT_DROP_ALERT_PERCENT,
        help="Alert when current price drops by this percent vs last run (0 disables).",
    )
    parser.add_argument(
        "--history-file",
        default=DEFAULT_HISTORY_FILE,
        help="CSV file used to store price history.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override product name for single URL mode.",
    )
    parser.add_argument(
        "--dry-run-email",
        action="store_true",
        help="Do not send email; print the alert payload instead.",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Fail instead of prompting for URL input when none is provided.",
    )
    return parser.parse_args()


def extract_asin(url: str) -> str | None:
    patterns = [
        r"/dp/([A-Z0-9]{10})(?:[/?]|$)",
        r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)",
        r"/gp/aw/d/([A-Z0-9]{10})(?:[/?]|$)",
        r"/([A-Z0-9]{10})(?:[/?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def first_price_text(soup: BeautifulSoup) -> str | None:
    selectors = [
        "span.a-price.a-text-price span.a-offscreen",
        "span.a-price span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#price_inside_buybox",
        "span.a-price-whole",
        "span.a-offscreen",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return node.get_text(strip=True)
    return None


def infer_product_name(soup: BeautifulSoup) -> str | None:
    title_node = soup.select_one("#productTitle")
    if title_node and title_node.get_text(strip=True):
        return title_node.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return None


def normalize_price(text: str) -> float:
    match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
    if not match:
        raise ValueError(f"Unable to parse numeric price from: {text!r}")
    return float(match.group(1).replace(",", ""))


def send_email(subject: str, body: str, dry_run: bool = False) -> None:
    if dry_run:
        print("[dry-run-email] Subject:", subject)
        print("[dry-run-email] Body:\n" + body)
        return

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Email skipped: set EMAIL_ADDRESS and EMAIL_PASSWORD in .env.")
        return

    message = MIMEMultipart()
    message["From"] = EMAIL_ADDRESS
    message["To"] = EMAIL_ADDRESS
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_ADDRESS, 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message.as_string())
        print(f"Email alert sent to {EMAIL_ADDRESS}")
    except Exception as exc:
        print(f"Email error: {exc}")


def read_urls_from_file(path: str) -> list[str]:
    if path == "-":
        print("Reading URLs from stdin... (one URL per line; Ctrl-D to finish)")
        return [
            line.strip()
            for line in sys.stdin.read().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    file_path = Path(path)
    if not file_path.exists():
        print(f"URLs file not found: {file_path}")
        return []
    urls: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.urls_file:
        urls.extend(read_urls_from_file(args.urls_file))
    if args.url:
        urls.append(args.url)

    env_url = os.getenv("AMAZON_URL")
    if not urls and env_url:
        urls.append(env_url)

    if not urls and not args.no_prompt:
        print("No product URL provided.")
        print("Paste one or more Amazon product URLs (comma separated):")
        try:
            entered = input("Amazon URL(s): ").strip()
        except EOFError:
            entered = ""
        if entered:
            urls.extend([item.strip() for item in entered.split(",") if item.strip()])

    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def history_key(url: str, asin: str | None) -> str:
    return asin if asin else url


def load_last_prices(history_file: str) -> dict[str, float]:
    path = Path(history_file)
    if not path.exists():
        return {}
    last_prices: dict[str, float] = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = row.get("key")
                price = row.get("price")
                if key and price:
                    try:
                        last_prices[key] = float(price)
                    except ValueError:
                        continue
    except Exception:
        return {}
    return last_prices


def append_history(history_file: str, result: PriceResult) -> None:
    path = Path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as file:
        fields = ["timestamp_utc", "key", "url", "name", "price"]
        writer = csv.DictWriter(file, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "key": history_key(result.url, result.asin),
                "url": result.url,
                "name": result.name,
                "price": f"{result.price:.2f}",
            }
        )


def is_amazon_host(netloc: str) -> bool:
    host = netloc.lower().split(":", 1)[0]
    return host == "amazon.com" or host.endswith(".amazon.com")


def fetch_single_price(url: str, custom_name: str | None = None) -> tuple[str, float, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not is_amazon_host(parsed.netloc):
        raise ValueError("URL does not look like an Amazon link.")

    product_name = custom_name or "Amazon product"
    asin = extract_asin(url)
    offer_url = f"https://www.amazon.com/gp/offer-listing/{asin}" if asin else None
    price_text: str | None = None

    candidates = [url]
    if offer_url:
        candidates.append(offer_url)

    for candidate in candidates:
        try:
            response = requests.get(
                candidate, headers=DESKTOP_HEADERS, cookies=COOKIES, timeout=10
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        if custom_name is None:
            inferred = infer_product_name(soup)
            if inferred:
                product_name = inferred
        price_text = first_price_text(soup)
        if price_text:
            break

    if not price_text:
        mobile_url = f"https://www.amazon.com/gp/aw/d/{asin}" if asin else url
        try:
            response = requests.get(
                mobile_url, headers=MOBILE_HEADERS, cookies=COOKIES, timeout=10
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Unable to fetch product page: {exc}") from exc
        match = re.search(r"\$\s*([0-9][0-9,]*\.?[0-9]*)", response.text)
        price_text = match.group(0) if match else None

    if not price_text:
        raise RuntimeError("Price not found. Amazon may be region-restricting or blocking scraping.")

    return product_name, normalize_price(price_text), asin


def process_url(
    url: str,
    custom_name: str | None,
    last_prices: dict[str, float],
    history_file: str,
) -> PriceResult:
    name, price, asin = fetch_single_price(url, custom_name)
    key = history_key(url, asin)
    previous = last_prices.get(key)
    result = PriceResult(url=url, name=name, price=price, asin=asin, previous_price=previous)
    append_history(history_file, result)
    last_prices[key] = price
    return result


def maybe_alert(result: PriceResult, args: argparse.Namespace) -> None:
    reasons: list[str] = []
    if args.target and result.price < args.target:
        reasons.append(f"below target ${args.target:.2f}")
    if args.drop_alert and result.previous_price and result.previous_price > 0:
        drop_percent = ((result.previous_price - result.price) / result.previous_price) * 100
        if drop_percent >= args.drop_alert:
            reasons.append(f"dropped {drop_percent:.2f}% since last check")
    if not reasons:
        return

    subject = f"Price Alert: {result.name} is ${result.price:.2f}"
    body = (
        f"Price alert for: {result.name}\n\n"
        f"Current Price: ${result.price:.2f}\n"
        f"Reason: {', '.join(reasons)}\n"
        f"Product URL: {result.url}\n"
    )
    send_email(subject, body, dry_run=args.dry_run_email)


def display_result(result: PriceResult) -> None:
    print(f"{result.name}\nCurrent Price: ${result.price:.2f}\nURL: {result.url}")
    if result.previous_price is None:
        print("Last Seen Price: first time tracked")
    else:
        delta = result.price - result.previous_price
        direction = "down" if delta < 0 else "up" if delta > 0 else "unchanged"
        print(f"Last Seen Price: ${result.previous_price:.2f} ({direction} {abs(delta):.2f})")


def main() -> int:
    args = parse_args()
    urls = collect_urls(args)
    if not urls:
        print("No URL entered. Exiting.")
        return 1

    last_prices = load_last_prices(args.history_file)
    successes = 0
    failures = 0

    for url in urls:
        print(f"\nChecking: {url}")
        try:
            result = process_url(url, args.name if len(urls) == 1 else None, last_prices, args.history_file)
            display_result(result)
            maybe_alert(result, args)
            successes += 1
        except Exception as exc:
            print(f"Failed: {exc}")
            failures += 1

    print(f"\nDone. Successful checks: {successes}, Failed checks: {failures}")
    if successes == 0 and failures > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
