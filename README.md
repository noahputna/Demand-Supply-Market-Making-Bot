# DSBot: Demand-Supply Market Making Bot

## Overview

**DSBot** is a configurable agent designed for use in Flexemarkets simulations. It is capable of executing both **proactive** and **reactive** trading strategies. The bot simulates real-world market-making behaviour by leveraging price signals from a private market to place or respond to orders on a public exchange with a defined profit margin.

This project showcases how agents can bridge different market layers (private and public) to generate risk-free arbitratge opportunities - a foundation concept in market-making.

## Features
| Feature               | Description                                                             |
|-----------------------|-----------------------------------------------------------------------|
| Dual Mode Support     | Operates in **Proactive** or **Reactive** mode.                       |
| Profit Margin Logic   | Adds/ subtracts fixed margin to explot bid/ask spread.                |
| Role Awareness        | Dynamically updates role as BUYER or SELLER based on executed trades. |
| Private-Public Link   | Trades with the agent in private market, hedges on public market.     |
| Cancelation Handeling | Cancels stale or unmatched orders.                                    |

---

## Strategy Explained
### **Proactive Bot**
- Actively places **limit orders** on the public market based on signals from a private agent (e.g., wants to buy/sell).
- Ensures each order embeds a **minimum profit threshold** (`PROFIT_MARGIN`) bettween buy and sell sides.
- Once a public trade executes, it **fulfills** the private agent's order to close the position.
- This is where the bot performs market-making; it creates **liquidity** on the public market at profitable spreads and offsets the risk immediately via the private market - capturing the spread.

---

### **Reactive Bot**
- Monitros the **public market** for buy/sell orders.
- Reacts only if there's an opportunity to **sell at a premium or buy at a discount** relative to a fixed internal value.
- Once a trade is executed publicly, it **fulfills the matched order privately**, just like the proactive bot.
- Passively market-makes by reacting to market orders rather than initiating them.

## Market-Making Logic
The bot replicates real-world **market makers** who:
1. Quote both **buy** and **sell** prices.
2. Capture the **bid-ask spread** for profit.
3. Hedge or net off trades using another market (in this case, a private agent).

For example, if an agent in the private market wants to sell at $105:
- DSBot places a **public BUY order at $100** (`105 - profit_margin = 5`).
- If filled, it executes the private SELL at $105, mkaing a **risk-free $5 profit**.

---
## Usage
### Setup
```python
FM_ACCOUNT = "regular-idol"
FM_EMAIL = "FM_EMAIL"       # Replace with environment variable in real use.
FM_PASSWORD = "FM_PASSWORD" # Replace with environment variable in real use.
MARKETPLACE_ID = 1174
ROLE = 0                    # Role: 0 = BUYER, 1 = SELLER
BOT_TYPE = 0                # Bot Type: 0 = PROACTIVE, 1 = REACTIVE

ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, ROLE, BOT_TYPE)
ds_bot.run()
```
## Choose Bot Type
You'll be prompted to choose:

```ini
PROACTIVE = 0
REACTIVE = 1
```
Then, enter your desired profit margin (in cents):
```text
Enter desired profit margin:
```
