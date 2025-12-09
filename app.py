import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與排版
st.set_page_config(page_title="市場情緒量化投資儀表板 v2.1", page_icon="🧭", layout="wide")

st.title("🧭 市場情緒量化投資儀表板 v2.1")
st.markdown("依據「六大指標權重」計算綜合市場分數 (-8 ~ +8)，協助判斷進出場時機。")
st.markdown("---")

# ==========================================
# 1. 定義評分邏輯函數
# ==========================================

def get_fg_score(value):
    # 恐懼貪婪: 0-25(+2), 26-44(+1), 45-55(0), 56-74(-1), 75-100(-2)
    if value <= 25: return 2
    elif value <= 44: return 1
    elif value <= 55: return 0
    elif value <= 74: return -1
    else: return -2

def get_mcclellan_score(value):
    # McClellan: <=-100(+2), -100~-50(+1), -50~+50(0), +50~+100(-1), >100(-2)
    if value <= -100: return 2
    elif value <= -50: return 1
    elif value <= 50: return 0
    elif value <= 100: return -1
    else: return -2

def get_pc_score(value):
    # Put/Call: >=1.0(+2), 0.8-0.99(+1), 0.6-0.79(0), 0.5-0.59(-1), <0.5(-2)
    if value >= 1.0: return 2
    elif value >= 0.8: return 1
    elif value >= 0.6: return 0
    elif value >= 0.5: return -1
    else: return -2

def get_vix_score(value):
    # VIX: >=40(+2), 30-39(+1), 15-29(0), 12-14(-1), <12(-2)
    if value >= 40: return 2
    elif value >= 30: return 1
    elif value >= 15: return 0
    elif value >= 12: return -1
    else: return -2

def get_bias_score(value):
    # 200日乖離率: <=-20%(+2), -20~-10%(+1), -10~+10%(0), +10~+15%(-1), >+15%(-2)
    if value <= -20: return 2
    elif value <= -10: return 1
    elif value <= 10: return 0
    elif value <= 15: return -1
    else: return -2

def get_pe_score(value):
    # Forward P/E: <=15(+2), 15-18(+1), 18-22(0), 22-25(-1), >=25(-2)
    if value <= 15: return 2
    elif value < 18: return 1
    elif value <= 22: return 0
    elif value < 25: return -1
    else: return -2

# ==========================================
# 2. 自動抓取輔助數據 (VIX & SPX Bias)
# ==========================================
try:
    # 抓取 VIX
    vix_ticker = yf.Ticker("^VIX")
    vix_hist = vix_ticker.history(period="1d")
    default_vix = round(float(vix_hist['Close'].iloc[-1]), 2) if not vix_hist.empty else 15.0

    # 抓取 S&P 500 並計算乖離率
    spx_ticker = yf.Ticker("^GSPC")
    spx_hist = spx_ticker.history(period="300d")
    if not spx_hist.empty:
        current_price = spx_hist['Close'].iloc[-1]
        ma200 = spx_hist['Close'].rolling(window=200).mean().iloc[-1]
        bias_calc = ((current_price - ma200) / ma200) * 100
        default_bias = round(float(bias_calc), 2)
    else:
        default_bias = 5.0
except Exception:
    default_vix = 15.0
    default_bias = 5.0

# ==========================================
# 3. 側邊欄：輸入 6 大指標
# ==========================================
st.sidebar.header("📊 輸入今日指標數據")

# 1. Fear & Greed (15%)
st.sidebar.markdown("### 1. 恐懼貪婪指數 (15%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/charts/50108/cnn-fear-and-greed)")
in_fg = st.sidebar.number_input("輸入數值", value=50.00, step=0.01)

# 2. McClellan Oscillator (15%)
st.sidebar.markdown("### 2. McClellan Oscillator (15%)")
st.sidebar.markdown("[查詢連結 (McOscillator)](https://www.mcoscillator.com/market_breadth_data/)")
in_mcc = st.sidebar.number_input("輸入數值", value=0.000, step=0.001)

# 3. Put/Call Ratio (10%)
st.sidebar.markdown("### 3. Put/Call Ratio (10%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/charts/449/us-cboe-options-put-call-ratio)")
in_pc = st.sidebar.number_input("輸入數值", value=0.65, step=0.01)

# 4. VIX (15%)
st.sidebar.markdown("### 4. VIX 恐慌指數 (15%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/series/355/vix)")
in_vix = st.sidebar.number_input("輸入數值", value=default_vix, step=0.1)

# 5. 200日均線乖離率 (25%)
st.sidebar.markdown("### 5. S&P 500 200日乖離率 (25%)")
st.sidebar.markdown("[查詢連結 (Barchart)](https://www.barchart.com/stocks/quotes/$SPX/technical-analysis)")
st.sidebar.caption(f"系統試算參考值: {default_bias}%")
in_bias = st.sidebar.number_input("輸入百分比 (例如 5 代表 5%)", value=default_bias, step=0.1)

# 6. Forward P/E (20%)
st.sidebar.markdown("### 6. Forward P/E Ratio (20%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/series/20052/sp500-forward-pe-ratio)")
in_pe = st.sidebar.number_input("輸入數值 (例如 20.5)", value=20.0, step=0.1)

# ==========================================
# 4. 計算核心邏輯
# ==========================================
s1 = get_fg_score(in_fg)
s2 = get_mcclellan_score(in_mcc)
s3 = get_pc_score(in_pc)
s4 = get_vix_score(in_vix)
s5 = get_bias_score(in_bias)
s6 = get_pe_score(in_pe)

w1, w2, w3, w4, w5, w6 = 0.15, 0.15, 0.10, 0.15, 0.25, 0.20

weighted_sum = (
    (s1/2 * w1) + (s2/2 * w2) + (s3/2 * w3) +
    (s4/2 * w4) + (s5/2 * w5) + (s6/2 * w6)
)
final_score = round(weighted_sum * 8, 2)

# ==========================================
# 5. 主畫面顯示
# ==========================================
col1, col2 = st.columns([1, 1.5])

with col1:
    st.markdown("### 🎯 綜合市場情緒分數")
    
    status_label = ""
    if final_score >= 5: status_label = "💥 極度恐慌區 (強烈買進)"
    elif final_score >= 2: status_label = "😨 恐慌區 (分批買進)"
    elif final_score >= -1: status_label = "☁️ 正常區 (定期定額)"
    elif final_score >= -4: status_label = "🔥 偏熱區 (暫停加碼)"
    else: status_label = "🚨 過熱自滿區 (風險控管)"
    
    st.metric(label="範圍約 -8 ~ +8", value=f"{final_score} 分")
    st.info(f"目前狀態：**{status_label}**")

with col2:
    st.markdown("#### 📊 各指標原始得分")
    metrics_data = {
        "指標": ["恐懼貪婪", "McClellan", "Put/Call", "VIX", "200日乖離", "Forward P/E"],
        "輸入值": [in_fg, in_mcc, in_pc, in_vix, f"{in_bias}%", in_pe],
        "得分": [s1, s2, s3, s4, s5, s6]
    }
    st.dataframe(pd.DataFrame(metrics_data), hide_index=True)

st.markdown("---")

# ==========================================
# 6. 投資操作建議
# ==========================================
st.header("💡 投資操作建議")

if final_score >= 5:
    st.success("### 💎 極度恐慌區 (Score ≥ +5)")
    st.markdown("""
    * **狀態**：市場極度恐慌，最佳買點。
    * **操作**：當月扣款 **1.5～2 倍**；若有預備金可分批進場。
    * **提醒**：嚴禁槓桿與 All-in。
    """)
elif 2 <= final_score < 5:
    st.success("### 💰 恐慌區 (Score +2 ~ +4)")
    st.markdown("""
    * **狀態**：情緒恐懼，估值相對便宜。
    * **操作**：扣款提升為 **1.2～1.5 倍**；股票比重不足可溫和加碼。
    """)
elif -1 <= final_score < 2:
    st.info("### 🧘 正常區 (Score -1 ~ +1)")
    st.markdown("""
    * **狀態**：市場情緒與估值中性。
    * **操作**：**照原定計畫定期定額**，每半年做小幅再平衡。
    """)
elif -4 <= final_score < -1:
    st.warning("### 🔥 偏熱區 (Score -1 ~ -4)")
    st.markdown("""
    * **狀態**：市場開始貪婪，風險升高。
    * **操作**：**暫停主動加碼**，僅保留小額定投；檢視是否需獲利了結。
    """)
else:
    st.error("### 🚨 過熱自滿區 (Score < -4)")
    st.markdown("""
    * **狀態**：市場極度貪婪，隨時可能反轉。
    * **操作**：**不再新增股票部位**；將股票比重調降回原先目標 (再平衡)。
    """)

# ==========================================
# 7. (新增功能) 顯示完整給分標準表
# ==========================================
st.markdown("---")
with st.expander("📖 查看 6 大指標完整給分標準表 (點擊展開)", expanded=False):
    st.markdown("""
    **註**：+2 為極度恐慌/便宜 (買進訊號)，-2 為極度貪婪/昂貴 (賣出訊號)。
    """)
    
    tab1, tab2 = st.tabs(["情緒與波動指標", "價格與估值指標"])
    
    with tab1:
        st.markdown("#### 1. 恐懼貪婪指數 (Fear & Greed) [15%]")
        st.markdown("""
        | 數值範圍 | 分數 | 意義 |
        | :--- | :---: | :--- |
        | **0 – 25** | **+2** | 😱 極度恐慌 |
        | **26 – 44** | **+1** | 😨 恐懼 |
        | **45 – 55** | **0** | 😐 中性 |
        | **56 – 74** | **-1** | 🤑 貪婪 |
        | **75 – 100** | **-2** | 🚨 極度貪婪 |
        """)
        
        st.markdown("#### 2. McClellan Oscillator (廣度) [15%]")
        st.markdown("""
        | 數值範圍 | 分數 | 意義 |
        | :--- | :---: | :--- |
        | **≤ -100** | **+2** | 📉 極度超賣 (嚴重殺跌) |
        | **-100 ~ -50** | **+1** | 📉 超賣 |
        | **-50 ~ +50** | **0** | 😐 正常 |
        | **+50 ~ +100** | **-1** | 📈 偏超買 |
        | **> +100** | **-2** | 🚀 極度超買 |
        """)

        st.markdown("#### 3. Put/Call Ratio [10%] & 4. VIX [15%]")
        st.markdown("""
        | 分數 | Put/Call Ratio (避險情緒) | VIX (恐慌指數) |
        | :---: | :--- | :--- |
        | **+2** | **≥ 1.0** (極度悲觀) | **≥ 40** (極端恐慌) |
        | **+1** | **0.80 – 0.99** | **30 – 39** |
        | **0** | **0.60 – 0.79** | **15 – 29** |
        | **-1** | **0.50 – 0.59** | **12 – 14** |
        | **-2** | **< 0.50** (極度樂觀) | **< 12** (過度自滿) |
        """)

    with tab2:
        st.markdown("#### 5. S&P 500 對 200日均線乖離率 [25%]")
        st.markdown("""
        | 乖離率 (Bias) | 分數 | 意義 |
        | :--- | :---: | :--- |
        | **≤ -20%** | **+2** | 🏚️ 極度跌深 (熊市底部特徵) |
        | **-20% ~ -10%** | **+1** | 📉 明顯修正 |
        | **-10% ~ +10%** | **0** | ⚖️ 接近長期均值 |
        | **+10% ~ +15%** | **-1** | 📈 偏熱 (漲多) |
        | **> +15%** | **-2** | 🚀 明顯漲多 (風險高) |
        """)
        
        st.markdown("#### 6. S&P 500 Forward P/E (12M) [20%]")
        st.markdown("""
        | 本益比 (P/E) | 分數 | 意義 |
        | :--- | :---: | :--- |
        | **≤ 15** | **+2** | 💎 估值便宜 |
        | **15 – 18** | **+1** | 📉 略便宜~合理偏低 |
        | **18 – 22** | **0** | ⚖️ 合理區間 |
        | **22 – 25** | **-1** | 💸 偏貴 |
        | **≥ 25** | **-2** | 🚨 明顯昂貴 |
        """)
