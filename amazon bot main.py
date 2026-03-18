import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env if present.
load_dotenv()

# Configuration (safe fallbacks so the script always runs)
TARGET_PRICE = float(os.getenv("TARGET_PRICE", "150"))  # 0 disables alerts
SMTP_ADDRESS = os.getenv("SMTP_ADDRESS", "smtp.gmail.com")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "rubayet079@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "oxjucztiuoevqcf")

URL = "https://www.amazon.com/ASUS-ROG-Xbox-Ally-Touchscreen/dp/B0FM6C3ZMN"
ALT_URL = "https://www.amazon.com/gp/offer-listing/B0FM6C3ZMN"
MOBILE_URL = "https://www.amazon.com/gp/aw/d/B0FM6C3ZMN?psc=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15A372 Safari/604.1",
    "Accept-Language": "en-US,en;q=0.9",
}
COOKIES = {"i18n-prefs": "USD", "lc-main": "en_US"}

def first_price_text(soup: BeautifulSoup) -> str | None:
    selectors = [
        "span.a-price.a-text-price span.a-offscreen",
        "span.a-price span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#price_inside_buybox",
        "span.a-price-whole",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return node.get_text(strip=True)
    return None

def normalize_price(text: str) -> float:
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])
    return float(cleaned)

def send_email(product_name: str, current_price: float, product_url: str) -> None:
    # Create the email content
    subject = f"Price Alert: {product_name} is now ${current_price:.2f}"
    body = f"Good news! The price of {product_name} has dropped below your target price.\n\n" \
           f"Current Price: ${current_price:.2f}\n" \
           f"Buy Now: {product_url}"

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = EMAIL_ADDRESS
    message["To"] = EMAIL_ADDRESS
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Connect to the email server and send the email
    if not EMAIL_PASSWORD:
        print("Email not sent: EMAIL_PASSWORD not set. Set EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_ADDRESS to enable alerts.")
        return

    try:
        with smtplib.SMTP(SMTP_ADDRESS, 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message.as_string())
            print(f"Email sent successfully to {EMAIL_ADDRESS}")
    except Exception as e:
        print(f"Error sending email: {e}")

def fetch_price() -> None:
    price_text: str | None = None
    product_name = "ASUS ROG Ally"

    try:
        # Try desktop product and offer pages first
        for url in (URL, ALT_URL):
            response = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            price_text = first_price_text(soup)
            if price_text:
                break

        # Fallback: hit the mobile page and regex the first $price.
        if not price_text:
            mobile_resp = requests.get(MOBILE_URL, headers=MOBILE_HEADERS, cookies=COOKIES, timeout=10)
            mobile_resp.raise_for_status()
            match = re.search(r"\$\s*([0-9][0-9,]*\.?[0-9]*)", mobile_resp.text)
            price_text = match.group(0) if match else None
    except requests.RequestException as exc:
        print(f"Network error while fetching price: {exc}")
        return

    if not price_text:
        print("Error: Price element not found on the page. Amazon may be hiding it based on region or anti-bot rules.")
        return

    try:
        price_value = normalize_price(price_text)
        print(f"Current Price: ${price_value:.2f}")

        # Check if the price is below the target price
        if TARGET_PRICE and price_value < TARGET_PRICE:
            send_email(product_name, price_value, URL)
    except ValueError:
        print(f"Error: Price format seems different than expected. Raw text: {price_text!r}")
        return


if __name__ == "__main__":
    fetch_price()
