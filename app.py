import os
os.system('pip install yfinance pandas_ta matplotlib')

import streamlit as st
# ... โค้ดที่เหลือของคุณ ...

import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import matplotlib.pyplot as plt

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TradeLab AI Backtester", layout="wide")
st.title("📈 TradeLab AI: Professional Backtest Engine")
st.markdown("ระบบทดสอบกลยุทธ์อัตโนมัติ (Trend Following + Risk Management)")

# --- 2. Sidebar สำหรับปรับค่า (Input) ---
with st.sidebar:
    st.header("⚙️ Strategy Settings")
    symbol = st.selectbox("เลือกสินทรัพย์", ["SOL-USD", "ETH-USD", "BTC-USD", "AUDUSD=X", "GC=F"])
    start_date = st.date_input("วันที่เริ่มต้น", pd.to_datetime("2024-01-01"))
    
    st.divider()
    st.subheader("Indicators")
    sma_s = st.slider("เส้นค่าเฉลี่ยระยะสั้น (Short SMA)", 5, 20, 10)
    sma_l = st.slider("เส้นค่าเฉลี่ยระยะยาว (Long SMA)", 21, 100, 50)
    adx_min = st.slider("ค่า ADX ขั้นต่ำ (Trend Strength)", 10, 40, 20)

    st.divider()
    st.subheader("Risk Management")
    sl_pct = st.number_input("Stop Loss (%)", value=3.0) / 100
    ts_pct = st.number_input("Trailing Stop (%)", value=7.0) / 100

# --- 3. ส่วนการคำนวณ (Engine) ---
if st.button("🚀 Run Backtest"):
    with st.spinner('กำลังคำนวณผลลัพธ์...'):
        # ดึงข้อมูล
        raw_data = yf.download(symbol, start=start_date, interval='1d', auto_adjust=True)
        data = raw_data.copy()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # คำนวณ Indicators
        data['SMA_short'] = data['Close'].rolling(window=sma_s).mean()
        data['SMA_long'] = data['Close'].rolling(window=sma_l).mean()
        data.ta.adx(append=True)
        data = data.dropna().copy()

        # Logic จำลองการเทรด (เหมือนที่เราทำใน Colab)[span_1](start_span)[span_1](end_span)
        status, entry_price, highest_price = 0, 0, 0
        strat_returns = []

        for i in range(len(data)):
            current_price = data['Close'].iloc[i]
            adx_now = data['ADX_14'].iloc[i]
            ret = 0
            
            if status == 0:
                if (data['SMA_short'].iloc[i] > data['SMA_long'].iloc[i]) and (adx_now > adx_min):
                    status, entry_price, highest_price = 1, current_price, current_price
            elif status == 1:
                highest_price = max(highest_price, current_price)
                if current_price <= entry_price * (1 - sl_pct): # Stop Loss
                    ret, status = -sl_pct, 0
                elif current_price <= highest_price * (1 - ts_pct): # Trailing Stop[span_2](start_span)[span_2](end_span)
                    ret, status = (current_price - data['Close'].iloc[i-1])/data['Close'].iloc[i-1], 0
                elif data['SMA_short'].iloc[i] < data['SMA_long'].iloc[i]: # Exit Signal
                    ret, status = (current_price - data['Close'].iloc[i-1])/data['Close'].iloc[i-1], 0
                else:
                    ret = (current_price - data['Close'].iloc[i-1])/data['Close'].iloc[i-1]
            strat_returns.append(ret)

        data['Strategy_Returns'] = strat_returns
        data['Cumulative_Returns'] = (1 + data['Strategy_Returns']).cumprod()
        data['Peak'] = data['Cumulative_Returns'].cummax()
        data['Drawdown'] = (data['Cumulative_Returns'] - data['Peak']) / data['Peak']

        # --- 4. แสดงผลลัพธ์บนหน้าเว็บ ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Profit", f"{(data['Cumulative_Returns'].iloc[-1]-1)*100:.2f}%")
        col2.metric("Max Drawdown", f"{data['Drawdown'].min()*100:.2f}%")
        col3.metric("Final Value", f"{data['Cumulative_Returns'].iloc[-1]:.2f}x")

        st.subheader("Equity Curve & Drawdown Analysis")
        st.line_chart(data['Cumulative_Returns'])
        st.area_chart(data['Drawdown'])
