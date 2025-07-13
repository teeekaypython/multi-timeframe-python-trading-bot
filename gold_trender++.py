import MetaTrader5 as mt5
import time
from datetime import datetime, date
import pytz
import talib
import pandas as pd
import logging

# Initialize MetaTrader 5
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Account credentials
account = 'replace with yours'
password = "replace with yours"
server = "Deriv-Demo"
a
# Symbol and trading parameters
symbol = "XAUUSD"
lot = 0.1
deviation = 20
trade_open = False
position_id = None  # Keep track of the position ID

# Take profit and stop loss parameters
STOP_LOSS_POINTS = 700
TAKE_PROFIT_POINTS = 3000

TRAILING_STOP_POINTS = 700  # Trailing stop distance



def authenticate_account():
    """Authenticate the account with MetaTrader 5."""
    authenticate = mt5.login(account, password=password, server=server)
    if authenticate:
        logging.info("Authentication successful")
    else:
        logging.error(f"Authentication failed: {mt5.last_error()}")
        mt5.shutdown()
        quit()

def fetch_symbol_info():
    """Fetch real-time symbol info."""
    symbol_info = mt5.symbol_info_tick(symbol)
    if symbol_info is None:
        logging.error(f"Failed to get tick info for symbol {symbol}.")
        mt5.shutdown()
        quit()
    return symbol_info

def buy():
    global trade_open, position_id
    symbol_info = fetch_symbol_info()
    price = symbol_info.bid
    point = mt5.symbol_info(symbol).point
    stop_loss = price - STOP_LOSS_POINTS * point
    take_profit = price + TAKE_PROFIT_POINTS * point  # Set take profit 300,000 points above entry

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "magic": 234000,
        "symbol": symbol,
        "volume": lot,
        "sl": stop_loss,
        "tp": take_profit,  # Set take profit
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": deviation,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    if not trade_open:
        execute_order = mt5.order_send(request)
        if execute_order.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Buy order executed: {execute_order}")
            trade_open = True
            position_id = execute_order.order
        else:
            logging.error(f"Failed to execute buy order, retcode: {execute_order.retcode}")
    else:
        logging.warning("Trade already open, not opening another.")


def sell():
    global trade_open, position_id
    symbol_info = fetch_symbol_info()
    price = symbol_info.ask  # Use the ask price for sell orders
    point = mt5.symbol_info(symbol).point
    stop_loss = price + STOP_LOSS_POINTS * point
    take_profit = price - TAKE_PROFIT_POINTS * point  # Set take profit below the entry

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "magic": 234000,
        "symbol": symbol,
        "volume": lot,
        "sl": stop_loss,
        "tp": take_profit,  # Set take profit
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "comment": "python script open sell",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    if not trade_open:
        execute_order = mt5.order_send(request)
        if execute_order.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Sell order executed: {execute_order}")
            trade_open = True
            position_id = execute_order.order
        else:
            logging.error(f"Failed to execute sell order, retcode: {execute_order.retcode}")
    else:
        logging.warning("Trade already open, not opening another.")

# Modify the crossover logic to include sell conditions




def manage_open_positions():
    """Manage open positions (both buy and sell) and implement trailing stop loss."""
    global trade_open, position_id
    positions = mt5.positions_get(symbol=symbol)

    if positions is None or len(positions) == 0:
        trade_open = False  # No positions open
        position_id = None
        return
    else:
        trade_open = True
        for position in positions:
            position_id = position.ticket
            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point
            current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

            # Determine trailing stop logic based on position type (buy or sell)
            if position.type == mt5.POSITION_TYPE_BUY:
                new_stop_loss = current_price - TRAILING_STOP_POINTS * point
                current_stop_loss = position.sl

                # Update stop loss for buy position
                if current_stop_loss == 0.0:
                    current_stop_loss = -float('inf')  # No stop loss set
                if new_stop_loss > current_stop_loss:
                    # Modify the position to update the stop loss
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position_id,
                        "symbol": symbol,
                        "sl": new_stop_loss,
                        "tp": position.tp,  # Keep the current take profit
                    }
                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        logging.info(f"Updated stop loss to {new_stop_loss} for buy position {position_id}")
                    else:
                        logging.error(f"Failed to update stop loss for buy position {position_id}: {result.retcode}")

            elif position.type == mt5.POSITION_TYPE_SELL:
                new_stop_loss = current_price + TRAILING_STOP_POINTS * point  # Inverse logic for sell
                current_stop_loss = position.sl

                # Update stop loss for sell position
                if current_stop_loss == 0.0:
                    current_stop_loss = float('inf')  # No stop loss set
                if new_stop_loss < current_stop_loss:
                    # Modify the position to update the stop loss
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position_id,
                        "symbol": symbol,
                        "sl": new_stop_loss,
                        "tp": position.tp,  # Keep the current take profit
                    }
                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        logging.info(f"Updated stop loss to {new_stop_loss} for sell position {position_id}")
                    else:
                        logging.error(f"Failed to update stop loss for sell position {position_id}: {result.retcode}")


def close_position(position_id):
    global trade_open
    symbol_info = fetch_symbol_info()
    price = symbol_info.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "position": position_id,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script close",
        "type": mt5.ORDER_TYPE_SELL,  # Close the BUY position
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Position {position_id} closed successfully")
        trade_open = False
    else:
        logging.error(f"Failed to close position {position_id}: {result.retcode}")

# Function for fetching data and checking trading conditions
def functions():
    asset = symbol
    today_date = date.today()
    logging.info(f"Running trading function on {today_date}")

    time_zon = pytz.timezone('UTC')
    utc_from = datetime(2024, 12, 4, tzinfo=time_zon)

    # Fetch M1 data
    rates_m1 = mt5.copy_rates_from(asset, mt5.TIMEFRAME_M1, utc_from, 10000)
    logging.info("Fetched M1 market data")

    rates_frame_m1 = pd.DataFrame(rates_m1)
    rates_frame_m1['time'] = pd.to_datetime(rates_frame_m1['time'], unit='s')

    # Fetch M15 data
    rates_m15 = mt5.copy_rates_from(asset, mt5.TIMEFRAME_M15, utc_from, 10000)
    logging.info("Fetched M15 market data")

    rates_frame_m15 = pd.DataFrame(rates_m15)
    rates_frame_m15['time'] = pd.to_datetime(rates_frame_m15['time'], unit='s')

    # Fetch M30 data
    rates_m30 = mt5.copy_rates_from(asset, mt5.TIMEFRAME_M30, utc_from, 10000)
    logging.info("Fetched M30 market data")

    rates_frame_m30 = pd.DataFrame(rates_m30)
    rates_frame_m30['time'] = pd.to_datetime(rates_frame_m30['time'], unit='s')

    # Fetch 1H data
    rates_1H = mt5.copy_rates_from(asset, mt5.TIMEFRAME_H1, utc_from, 10000)
    logging.info("Fetched H1 market data")

    rates_frame_1H = pd.DataFrame(rates_1H)
    rates_frame_1H['time'] = pd.to_datetime(rates_frame_1H['time'], unit='s')


    # Fetch 4H data
    rates_4H = mt5.copy_rates_from(asset, mt5.TIMEFRAME_H4, utc_from, 10000)
    logging.info("Fetched H4 market data")

    rates_frame_4H = pd.DataFrame(rates_4H)
    rates_frame_4H['time'] = pd.to_datetime(rates_frame_4H['time'], unit='s')


    # Fetch 1d data
    rates_1D = mt5.copy_rates_from(asset, mt5.TIMEFRAME_D1, utc_from, 10000)
    logging.info("Fetched 1D market data")

    rates_frame_1D = pd.DataFrame(rates_1D)
    rates_frame_1D['time'] = pd.to_datetime(rates_frame_1D['time'], unit='s')

    # M1 data
    data_m1 = rates_frame_m1
    close_prices_m1 = data_m1['close']
    high_prices_m1 = data_m1['high']
    low_prices_m1 = data_m1['low']

    # M15 data
    data_m15 = rates_frame_m15
    close_prices_m15 = data_m15['close']
    low_prices_m15 = data_m15['low']
    high_prices_m15 = data_m15['high']

    # 1H data
    data_H1 = rates_frame_1H
    close_prices_h1 = data_H1['close']

    # h4 data
    data_h4 = rates_frame_4H
    close_prices_h4 = data_h4['close']

    # 1D data
    data_1D = rates_frame_1D
    close_prices_1D = data_1D['close']


    # Calculate MAs for M1
    sma = talib.SMA(close_prices_m1, 5)    # Small MA
    mma = talib.SMA(close_prices_m1, 12)   # Middle MA
    lma = talib.SMA(close_prices_m1, 20)   # Large MA
    ma200_m1 = talib.SMA(close_prices_m1, 200)  # 200-period MA for M1

    # Calculate MAs for M15
    ma5_m15 = talib.SMA(close_prices_m15, 5)  # 200-period MA for M15
    ma12_m15 = talib.SMA(close_prices_m15, 12)  # 200-period MA for M15
    ma20_m15 = talib.SMA(close_prices_m15, 20)  # 200-period MA for M15
    ma200_m15 = talib.SMA(close_prices_m15, 200)  # 200-period MA for M15


    # Calculate MAs for 1H
    ma10_1h = talib.SMA(close_prices_h1, 10)  # 200-period MA for M15
    ma20_1h = talib.SMA(close_prices_h1, 20)


    # Calculate MAs for 4h
    ma20_4h = talib.SMA(close_prices_h4, 20)  # 200-period MA for M15
    ma5_4h = talib.SMA(close_prices_h4, 5)
    ma10_4h = talib.SMA(close_prices_h4, 10)


     # Calculate MAs for 1D
    ma10_1D = talib.SMA(close_prices_1D, 10)


    # Stochastic for M1
    stoch_k, stoch_d = talib.STOCH(high_prices_m15, low_prices_m15, close_prices_m15,
                                   fastk_period=14, slowk_period=3, slowk_matype=0,
                                   slowd_period=3, slowd_matype=0)



    # Create a DataFrame for M1 relevant data
    ma_df = pd.DataFrame()
    ma_df['time'] = data_m1['time']
    ma_df['close'] = data_m1['close']
    ma_df["sma"] = sma
    ma_df['mma'] = mma
    ma_df["lma"] = lma
    ma_df['ma200_m1'] = ma200_m1
    ma_df['stochastic_low'] = stoch_k
    ma_df['stochastic_high'] = stoch_d

    ma_df.dropna(inplace=True)

    # Get the most recent price and MA from M15
    latest_close_m15 = close_prices_m15.iloc[-1]
    latest_ma5_m15 = ma5_m15.iloc[-1]
    latest_ma12_m15 = ma12_m15.iloc[-1]
    latest_ma20_m15 = ma20_m15.iloc[-1]
    latest_ma200_m15 = ma200_m15.iloc[-1]


    # Get the most recent price and MA from H4
    latest_close_h4 = close_prices_h4.iloc[-1]
    latest_ma20_h4 = ma20_4h.iloc[-1]
    latest_ma10_h4 = ma10_4h.iloc[-1]


     # Get the most recent price and MA from H1
    latest_close_h1 = close_prices_h1.iloc[-1]
    latest_ma10_h1 = ma10_1h.iloc[-1]


     # Get the most recent price and MA from 1D
    latest_close_1D = close_prices_1D.iloc[-1]
    latest_ma10_1D = ma10_1D.iloc[-1]

    latest_stoch_k= stoch_k.iloc[-1]
    latest_stoch_d = stoch_d.iloc[-1]




    if latest_close_1D>latest_ma10_1D and latest_close_h4 >latest_ma10_h4 and latest_close_h1>latest_ma10_h1:
        if latest_stoch_k < 30 and latest_stoch_k > latest_stoch_d:
            # Check that Stochastic K was previously below Stochastic D (to confirm crossover)
            previous_stoch_k = stoch_k.iloc[-2]
            previous_stoch_d = stoch_d.iloc[-2]

            if previous_stoch_k < previous_stoch_d:

                if not trade_open:
                    logging.info("Buying - M1 and M15 conditions met")
                    buy()
        else:
            logging.info("Trade already open, waiting for closure before next trade")


    elif latest_close_1D<latest_ma10_1D and latest_close_h4 <latest_ma10_h4 and latest_close_h1<latest_ma10_h1:

        if latest_stoch_k > 70 and latest_stoch_k < latest_stoch_d:
            # Check that Stochastic K was previously below Stochastic D (to confirm crossover)
            previous_stoch_k = stoch_k.iloc[-2]
            previous_stoch_d = stoch_d.iloc[-2]

            if previous_stoch_k > previous_stoch_d:

                if not trade_open:
                    logging.info("Selling - M1 and M15 conditions met")
                    sell()
        else:
            logging.info("Trade already open, waiting for closure before next trade")
    else:
        logging.info("No clear trend or M15 conditions not met, not entering any trade")

# Set up logging
logging.basicConfig(filename='trade_logs.txt',
                    filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

authenticate_account()

# Main loop
while True:
    try:

        functions()  # Check market data and trading conditions
        manage_open_positions()  # Manage open positions and trailing stop loss
    except Exception as e:
        logging.error(f"Error in trading logic: {e}")
    time.sleep(60)  # Run every 60 secon


