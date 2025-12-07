#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 16:36:43 2025

@author: yjc
"""

import streamlit as st
import yfinance as yf

# 設定網頁標題與排版
st.set_page_config(page_title="市場情緒量化指標", page_icon="📈")

st.title("📈 市場情緒量化投資儀表板")
st.markdown("---")

# 定義計分邏輯函數
def calculate_score(fear_greed, mcclellan, put_call, vix):
    score = 0
    details = []

    # 1. Fear & Greed Index
    # 邏輯：≤20 (+2), 30-70 (0), ≥80 (-2)
    s1 = 0
    if fear_greed <= 20:
        s1 = 2
    elif fear_greed >= 80:
        s1 = -2
    else:
        s1 = 0 # 包含 30-70 以及中間模糊地帶，視為中性
    score += s1
    details.append(f"恐懼貪婪 ({fear_greed}): {s1:+d} 分")

    # 2. McClellan Oscillator
    # 邏輯：≤-80 (+2), -40~+40 (0), ≥70 (-2)
    s2 = 0
    if mcclellan <= -80:
        s2 = 2
    elif mcclellan >= 70:
        s2 = -2
    elif -40 <= mcclellan <= 40:
        s2 = 0
    else:
        s2 = 0 # 模糊地帶視為中性
    score += s2
    details.append(f"McClellan ({mcclellan}): {s2:+d} 分")

    # 3. Put/Call Ratio
    # 邏輯：≥0.9 (+2), 0.5-0.8 (0), ≤0.5 (-2)
    # 註：假設 >0.9 為極度恐慌（看多訊號），<0.5 為極度樂觀
    s3 = 0
    if put_call >= 0.9:
        s3 = 2
    elif put_call <= 0.5:
        s3 = -2
    else:
        s3 = 0
    score += s3
    details.append(f"Put/Call Ratio ({put_call}): {s3:+d} 分")

    # 4. VIX
    # 邏輯：≥30 (+2), ≥40 (+3), 15-25 (0), ≤12 (-2)
    s4 = 0
    if vix >= 40:
        s4 = 3
    elif vix >= 30:
        s4 = 2
    elif vix <= 12:
        s4 = -2
    elif 15 <= vix <= 25:
        s4 = 0
    else:
        s4 = 0 # 12-15 或 25-30 視為中性或過渡區
    score += s4
    details.append(f"VIX ({vix}): {s4:+d} 分")

    return score, details

# --- 側邊欄：輸入數據 ---
st.sidebar.header("📊 輸入今日指標數據")

# 嘗試自動抓取 VIX
try:
    vix_data = yf.Ticker("^VIX")
    vix_today = vix_data.history(period="1d")['Close'].iloc[-1]
    vix_default = round(float(vix_today), 2)
    st.sidebar.success(f"已自動抓取 VIX: {vix_default}")
except:
    vix_default = 15.00
    st.sidebar.warning("無法抓取 VIX，請手動輸入")

# 建立輸入欄位與參考連結
st.sidebar.markdown("### 1. 恐懼貪婪指數")
st.sidebar.markdown("[點此查詢 (Macromicro)](https://en.macromicro.me/charts/50108/cnn-fear-and-greed)")
input_fg = st.sidebar.number_input("輸入數值", value=50, step=1, key="fg")

st.sidebar.markdown("### 2. McClellan Oscillator")
st.sidebar.markdown("[點此查詢 (McOscillator)](https://www.mcoscillator.com/market_breadth_data/)")
input_mcc = st.sidebar.number_input("輸入數值", value=0, step=1, key="mcc")

st.sidebar.markdown("### 3. Put/Call Ratio")
st.sidebar.markdown("[點此查詢 (Macromicro)](https://en.macromicro.me/charts/449/us-cboe-options-put-call-ratio)")
input_pc = st.sidebar.number_input("輸入數值", value=0.65, step=0.01, format="%.2f", key="pc")

st.sidebar.markdown("### 4. VIX 恐慌指數")
st.sidebar.markdown("[點此查詢 (Macromicro)](https://en.macromicro.me/series/355/vix)")
input_vix = st.sidebar.number_input("輸入數值", value=vix_default, step=0.1, format="%.2f", key="vix")

# --- 主畫面：計算與顯示 ---

total_score, score_details = calculate_score(input_fg, input_mcc, input_pc, input_vix)

col1, col2 = st.columns([1, 2])

with col1:
    st.metric(label="市場情緒總分", value=f"{total_score} 分")

with col2:
    st.write("#### 各項得分詳情：")
    for detail in score_details:
        st.text(detail)

st.markdown("---")

# --- 投資建議邏輯 ---
st.header("💡 投資操作建議")

if total_score >= 5:
    st.error("🚨 **恐慌區 (總分 ≥ +5)**")
    st.markdown("""
    * **狀態**：市場極度恐慌，這是最佳買點。
    * **行動**：**積極分批買入**。
    * **資金設定**：當月 ETF 扣款金額調成平常的 **1.5～2 倍**。
    * **備註**：若手上有預備現金，可啟動一部分進場。
    """)

elif 0 <= total_score <= 4:
    st.info("☁️ **正常區 (總分 0 ～ +4)**")
    st.markdown("""
    * **狀態**：市場情緒平穩或略微保守。
    * **行動**：**照原定計畫定期定額**。
    * **資金設定**：維持標準扣款金額。
    """)

elif -4 <= total_score <= -1:
    st.warning("🔥 **偏熱區 (總分 -1 ～ -4)**")
    st.markdown("""
    * **狀態**：市場開始興奮，風險逐漸升高。
    * **行動**：**暫停加碼 / 僅做小額扣款**。
    * **資金設定**：適度檢視資產配置，檢查股票比重是否過高。
    """)

elif total_score <= -5:
    st.success("💥 **過熱 & 自滿區 (總分 ≤ -5)**") # 使用 Success 顏色反向提醒獲利了結/風控
    st.markdown("""
    * **狀態**：市場極度貪婪，隨時可能反轉。
    * **行動**：**做風險控管 / 資產再平衡**。
    * **資金設定**：
        1. **不再新增**股票部位。
        2. 將股票部位調回原先目標（例如 80% 降回 60–70%）。
    """)

# 顯示計分標準表圖供參考 (您可以自行截圖上傳或省略)
with st.expander("查看計分標準參考表"):
    st.markdown("""
    | 指標 | 恐慌 / 超賣 (+分) | 中性 (0分) | 貪婪 / 過熱 (-分) |
    | :--- | :--- | :--- | :--- |
    | **Fear & Greed** | ≤ 20 (+2) | 30-70 | ≥ 80 (-2) |
    | **McClellan Osc** | ≤ -80 (+2) | -40~+40 | ≥ 70 (-2) |
    | **Put/Call Ratio** | ≥ 0.9 (+2) | 0.5-0.8 | ≤ 0.5 (-2) |
    | **VIX** | ≥ 30 (+2), ≥ 40 (+3) | 15-25 | ≤ 12 (-2) |
    """)