# multi-timeframe-python-trading-bot
This project is an automated trading bot that operates on MetaTrader 5 (MT5) using Python. It evaluates technical indicators across multiple timeframes (M1, M15, H1, H4, and D1) and places buy or sell trades when strict trend and momentum conditions are met. The bot also manages open trades with a dynamic trailing stop loss system and avoids duplicate trades.

✅ MT5 Integration using the official MetaTrader5 Python package

🧠 Multi-Timeframe Analysis:

D1, H4, and H1 for trend confirmation

M15 and M1 for signal entry via Stochastic crossover

📈 Technical Indicators:

Simple Moving Averages (SMA)

Stochastic Oscillator (K and D)

💡 Trading Logic:

Executes Buy when price is above MA10 across D1, H4, and H1 with bullish Stochastic crossover.

Executes Sell when price is below MA10 across D1, H4, and H1 with bearish Stochastic crossover.

🔄 Trade Management:

One trade per asset at a time.

Implements trailing stop loss updates based on live price.

🧼 Logging:

Logs all activity to trade_logs.txt for debugging and tracking.

🛡️ Fail-Safe Handling:

Catches and logs exceptions without crashing the bot.
