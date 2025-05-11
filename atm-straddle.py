import yfinance as yf
import pandas as pd
import numpy as np
import argparse
import csv
import os
from datetime import datetime, date

# Argument parser setup
parser = argparse.ArgumentParser(description="ATM Straddle Calculator")
parser.add_argument("symbol", type=str, help="Stock symbol, e.g. AAPL")
args = parser.parse_args()

symbol = args.symbol.upper()
stock = yf.Ticker(symbol)

# Fetch current stock price
hist_data = stock.history(period="1d")
if hist_data.empty:
    print(f"No historical data available for {symbol}.")
    exit()

current_price = hist_data['Close'].iloc[-1]
print(f"\nCurrent stock price for {symbol}: ${current_price:.2f}")

# Get option expiration dates
expirations = stock.options[:4]  # Limit to next 4 expirations
if not expirations:
    print("No option data available.")
    exit()

# Estimate HV
hist = stock.history(period="1mo")
returns = hist['Close'].pct_change().dropna()
hv = np.std(returns) * np.sqrt(252)

# Get earnings date
try:
    earnings_df = stock.calendar
    if isinstance(earnings_df, pd.DataFrame) and 'Earnings Date' in earnings_df.index:
        earnings_date = earnings_df.loc['Earnings Date'].iloc[0].strftime('%Y-%m-%d')
    else:
        earnings_date = "N/A"
except Exception:
    earnings_date = "N/A"

# CSV setup
csv_file = "straddle_results.csv"
fieldnames = [
    "Symbol", "Date", "Current Price", "Expiration Date", "DTE", "ATM Strike",
    "Call Price", "Call IV", "Call Delta", "Call Theta",
    "Put Price", "Put IV", "Put Delta", "Put Theta",
    "HV", "Straddle Price", "Implied Move %", "Range Low", "Range High", "Earnings Date"
]

file_exists = os.path.isfile(csv_file)

with open(csv_file, mode='a', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()

    for exp_date in expirations:
        try:
            opt_chain = stock.option_chain(exp_date)
            calls = opt_chain.calls
            puts = opt_chain.puts
        except:
            print(f"Error retrieving option chain for {exp_date}.")
            continue

        atm_strike = min(calls['strike'], key=lambda x: abs(x - current_price))

        atm_call_rows = calls[calls['strike'] == atm_strike]
        atm_put_rows = puts[puts['strike'] == atm_strike]

        if atm_call_rows.empty or atm_put_rows.empty:
            print(f"No ATM options found at strike {atm_strike} for expiration {exp_date}.")
            continue

        atm_call = atm_call_rows.iloc[0]
        atm_put = atm_put_rows.iloc[0]

        call_mid = (atm_call['bid'] + atm_call['ask']) / 2
        put_mid = (atm_put['bid'] + atm_put['ask']) / 2

        call_iv = atm_call['impliedVolatility']
        call_delta = atm_call.get('delta', 0)
        call_theta = atm_call.get('theta', 0)

        put_iv = atm_put['impliedVolatility']
        put_delta = atm_put.get('delta', 0)
        put_theta = atm_put.get('theta', 0)

        straddle_price = call_mid + put_mid
        implied_move_pct = (straddle_price / current_price) * 100
        low_range = current_price - straddle_price
        high_range = current_price + straddle_price

        # Calculate DTE
        dte = (datetime.strptime(exp_date, "%Y-%m-%d").date() - date.today()).days

        print(f"\nExpiration: {exp_date} | ATM Strike: {atm_strike} | DTE: {dte}")
        print(f"Call (mid): ${call_mid:.2f}, IV: {call_iv:.2%}, Delta: {call_delta}, Theta: {call_theta}")
        print(f"Put  (mid): ${put_mid:.2f}, IV: {put_iv:.2%}, Delta: {put_delta}, Theta: {put_theta}")
        print(f"Straddle Price: ${straddle_price:.2f}, Implied Move: ±{implied_move_pct:.2f}%")
        print(f"Expected Range: ${low_range:.2f} to ${high_range:.2f}")

        writer.writerow({
            "Symbol": symbol,
            "Date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "Current Price": round(current_price, 2),
            "Expiration Date": exp_date,
            "DTE": dte,
            "ATM Strike": atm_strike,
            "Call Price": round(call_mid, 2),
            "Call IV": round(call_iv, 4),
            "Call Delta": round(call_delta, 4),
            "Call Theta": round(call_theta, 4),
            "Put Price": round(put_mid, 2),
            "Put IV": round(put_iv, 4),
            "Put Delta": round(put_delta, 4),
            "Put Theta": round(put_theta, 4),
            "HV": round(hv, 4),
            "Straddle Price": round(straddle_price, 2),
            "Implied Move %": round(implied_move_pct, 2),
            "Range Low": round(low_range, 2),
            "Range High": round(high_range, 2),
            "Earnings Date": earnings_date
        })

print(f"\nResults saved to {csv_file}")
