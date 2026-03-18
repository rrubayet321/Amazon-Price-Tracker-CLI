# Product Brief: Amazon Price Tracker CLI

## Problem

Online shoppers forget to re-check product prices and miss price drops.

## Target User

- Budget-conscious online shoppers
- Students learning automation and CLI tooling
- Hobbyists tracking multiple products

## Value Proposition

Track prices automatically with history and actionable alerts, using a simple CLI workflow.

## Core Jobs To Be Done

- Track one product quickly
- Track many products in one run
- Understand if price moved up/down since last check
- Notify when a price target or significant drop condition is met

## Current Scope (v1)

- Single and batch URL tracking
- CSV price history
- Target and percentage-drop alerts
- Optional email notifications
- Interactive no-argument mode

## Success Metrics

- Setup completion rate (first successful run)
- Weekly active trackers (runs per user/week)
- Alert usefulness (alerts that lead to purchase decisions)
- Batch reliability (successful checks / total checks)

## Roadmap

1. `v1.1`: Add scheduler helper (`cron`/Task Scheduler templates)
2. `v1.2`: Add Telegram/Discord notification channel
3. `v1.3`: Web dashboard for history charts
4. `v2.0`: Multi-retailer support beyond Amazon
