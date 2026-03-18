# Amazon Price Tracker CLI

A product-style Python CLI to track Amazon prices, store history, and trigger email alerts.

## Features

- Track a single product or a batch of products.
- Parse common Amazon URL formats (`/dp/`, `/gp/product/`, `/gp/aw/d/`).
- Save price history to CSV.
- Show price movement since last check.
- Alert by absolute threshold (`--target`) or percent drop (`--drop-alert`).
- Interactive prompt when no URL is provided.

## Quick Start

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your config:

```bash
cp .env.example .env
```

4. Run:

```bash
python amazon_price_tracker.py "https://www.amazon.com/dp/B0FM6C3ZMN"
```

## Usage

```bash
python amazon_price_tracker.py [url] [--urls-file FILE|-] [--target PRICE] [--drop-alert PERCENT] [--history-file FILE] [--dry-run-email] [--no-prompt]
```

Examples:

```bash
# Single URL
python amazon_price_tracker.py "https://www.amazon.com/dp/B0FM6C3ZMN"

# Batch mode
python amazon_price_tracker.py --urls-file urls.txt

# Batch mode from stdin
cat urls.txt | python amazon_price_tracker.py --urls-file - --no-prompt

# Alert if below target
python amazon_price_tracker.py "https://www.amazon.com/dp/B0FM6C3ZMN" --target 500

# Alert if dropped >= 5% since last run
python amazon_price_tracker.py "https://www.amazon.com/dp/B0FM6C3ZMN" --drop-alert 5
```

## URL File Format

Create a `urls.txt` file with one URL per line:

```text
https://www.amazon.com/dp/B0FM6C3ZMN
https://www.amazon.com/gp/product/B0FM6C3ZMN
```

Lines starting with `#` are ignored.

Use `-` as the file path to read URLs from standard input.

## Environment Variables

See `.env.example` for all options.

- `AMAZON_URL`: default URL if no CLI URL is provided.
- `TARGET_PRICE`: default threshold for target alert.
- `DROP_ALERT_PERCENT`: default threshold for drop-percentage alert.
- `PRICE_HISTORY_FILE`: CSV history path.
- `SMTP_ADDRESS`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`: email alert settings.

## Product Notes

- Price scraping may fail for some products due to Amazon anti-bot/region restrictions.
- Use this tool responsibly and respect website terms.

## Security Guardrails

- CI secret scanning runs on pushes and pull requests via GitHub Actions (`gitleaks`).
- Optional local pre-commit scanning:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```
