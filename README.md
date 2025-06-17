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
