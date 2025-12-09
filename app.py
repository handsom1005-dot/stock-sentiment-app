import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與排版
st.set_page_config(page_title="市場情緒量化投資儀表板 v2.0", page_icon="🧭", layout="wide")

st.title("🧭 市場情緒量化投資儀表板 v2.0")
st.markdown("依據「六大指標權重」計算綜合市場分數 (-8 ~ +8)，協助判斷進出場時機。")
st.markdown("---")

# ==========================================
# 1. 定義評分邏輯函數 (依照 PDF 規則)
# ==========================================

def get_fg_score(value):
    # 恐懼貪婪: 0-25(+2), 26-44(+1), 45-55(0), 56-74(-1), 75-100(-2) [cite: 13-17]
    if value <= 25: return 2
    elif value <= 44: return 1
    elif value <= 55: return 0
    elif value <= 74: return -1
    else: return -2

def get_mcclellan_score(value):
    # McClellan: <=-100(+2), -100~-50(+1), -50~+50(0), +50~+100(-1), >100(-2) [cite: 23-27]
    if value <= -100: return 2
    elif value <= -50: return 1
    elif value <= 50: return 0
    elif value <= 100: return -1
    else: return -2

def get_pc_score(value):
    # Put/Call: >=1.0(+2), 0.8-0.99(+1), 0.6-0.79(0), 0.5-0.59(-1), <0.5(-2) [cite: 32-36]
    if value >= 1.0: return 2
    elif value >= 0.8: return 1
    elif value >= 0.6: return 0
    elif value >= 0.5: return -1
    else: return -2

def get_vix_score(value):
    # VIX: >=40(+2), 30-39(+1), 15-29(0), 12-14(-1), <12(-2) [cite: 41-45]
    if value >= 40: return 2
    elif value >= 30: return 1
    elif value >= 15: return 0
    elif value >= 12: return -1
    else: return -2

def get_bias_score(value):
    # 200日乖離率: <=-20%(+2), -20~-10%(+1), -10~+10%(0), +10~+15%(-1), >+15%(-2) [cite: 51-54]
    # 輸入值為百分比整數 (例如 15 代表 15%)
    if value <= -20: return 2
    elif value <= -10: return 1
    elif value <= 10: return 0
    elif value <= 15: return -1
    else: return -2

def get_pe_score(value):
    # Forward P/E: <=15(+2), 15-18(+1), 18-22(0), 22-25(-1), >=25(-2) [cite: 59-63]
    # 注意 PDF 邊界重疊部分，這裡採用常見邏輯劃分
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
    spx_hist = spx_ticker.history(period="300d") # 抓足夠天數算均線
    if not spx_hist.empty:
        current_price = spx_hist['Close'].iloc[-1]
        ma200 = spx_hist['Close'].rolling(window=200).mean().iloc[-1]
        # 公式: (Price - 200DMA) / 200DMA * 100
        bias_calc = ((current_price - ma200) / ma200) * 100
        default_bias = round(float(bias_calc), 2)
    else:
        default_bias = 5.0
except Exception as e:
    default_vix = 15.0
    default_bias = 5.0

# ==========================================
# 3. 側邊欄：輸入 6 大指標
# ==========================================
st.sidebar.header("📊 輸入今日指標數據")

# 1. Fear & Greed (15%)
st.sidebar.markdown("### 1. 恐懼貪婪指數 (15%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/charts/50108/cnn-fear-and-greed)")
in_fg = st.sidebar.number_input("輸入數值 (0-100)", value=50, step=1)

# 2. McClellan Oscillator (15%)
st.sidebar.markdown("### 2. McClellan Oscillator (15%)")
st.sidebar.markdown("[查詢連結 (McOscillator)](https://www.mcoscillator.com/market_breadth_data/)")
in_mcc = st.sidebar.number_input("輸入數值", value=0, step=1)

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
st.sidebar.caption(f"系統試算參考值: {default_bias}% (可手動修改)")
in_bias = st.sidebar.number_input("輸入百分比 (例如 5 代表 5%)", value=default_bias, step=0.1)

# 6. Forward P/E (20%)
st.sidebar.markdown("### 6. Forward P/E Ratio (20%)")
st.sidebar.markdown("[查詢連結 (MacroMicro)](https://en.macromicro.me/series/20052/sp500-forward-pe-ratio)")
in_pe = st.sidebar.number_input("輸入數值 (例如 20.5)", value=20.0, step=0.1)

# ==========================================
# 4. 計算核心邏輯
# ==========================================

# 取得原始分數 (-2 ~ +2)
s1 = get_fg_score(in_fg)
s2 = get_mcclellan_score(in_mcc)
s3 = get_pc_score(in_pc)
s4 = get_vix_score(in_vix)
s5 = get_bias_score(in_bias)
s6 = get_pe_score(in_pe)

# 權重設定 [cite: 67]
w1, w2, w3, w4, w5, w6 = 0.15, 0.15, 0.10, 0.15, 0.25, 0.20

# 計算加權平均 (先除以2標準化為 -1~1，再乘權重) [cite: 72-73]
weighted_sum = (
    (s1/2 * w1) +
    (s2/2 * w2) +
    (s3/2 * w3) +
    (s4/2 * w4) +
    (s5/2 * w5) +
    (s6/2 * w6)
)

# 最終分數放大 8 倍 (-8 ~ +8) [cite: 74]
final_score = weighted_sum * 8
final_score = round(final_score, 2)

# ==========================================
# 5. 主畫面顯示
# ==========================================

col1, col2 = st.columns([1, 1.5])

with col1:
    st.markdown("### 🎯 綜合市場情緒分數")
    
    # 根據分數給予顏色
    score_color = "normal"
    if final_score >= 2: score_color = "off" # Greenish equivalent for panic (buy)
    elif final_score <= -2: score_color = "inverse" # Reddish equivalent for greed (sell)
    
    st.metric(label="範圍約 -8 ~ +8", value=f"{final_score} 分")
    
    # 顯示目前區間標籤
    status_label = ""
    if final_score >= 5: status_label = "💥 極度恐慌區 (強烈買進)"
    elif final_score >= 2: status_label = "😨 恐慌區 (分批買進)"
    elif final_score >= -1: status_label = "☁️ 正常區 (定期定額)"
    elif final_score >= -4: status_label = "🔥 偏熱區 (暫停加碼)"
    else: status_label = "🚨 過熱自滿區 (風險控管)"
    
    st.info(f"目前狀態：**{status_label}**")

with col2:
    st.markdown("#### 📊 各指標原始得分 (-2 ~ +2)")
    metrics_data = {
        "指標": ["恐懼貪婪", "McClellan", "Put/Call", "VIX", "200日乖離", "Forward P/E"],
        "輸入值": [in_fg, in_mcc, in_pc, in_vix, f"{in_bias}%", in_pe],
        "原始得分": [s1, s2, s3, s4, s5, s6],
        "權重": ["15%", "15%", "10%", "15%", "25%", "20%"]
    }
    df = pd.DataFrame(metrics_data)
    st.dataframe(df, hide_index=True)

st.markdown("---")

# ==========================================
# 6. 投資操作建議 (五個區間)
# ==========================================
st.header("💡 投資操作建議")

# 邏輯區間 
if final_score >= 5:
    st.success("### 💎 極度恐慌區 (Score ≥ +5)")
    st.markdown("""
    * **狀態**：市場極度恐慌，這是最佳買點。
    * **資金操作**：
        1.  當月 ETF 扣款金額調成平時的 **1.5～2 倍**。
        2.  若有預備現金 (退休金、預備金)，可啟動部分進場 (分 3-6 批)。
    * **提醒**：嚴格避免槓桿與短線 All-in，預期可能還有 10-15% 跌幅。
    """)

elif 2 <= final_score < 5: # 包含 2~4.99
    st.success("### 💰 恐慌區 (Score +2 ~ +4)")
    st.markdown("""
    * **狀態**：情緒恐懼，估值低於牛市平均。
    * **資金操作**：
        1.  ETF 扣款金額提升為平時的 **1.2～1.5 倍**。
        2.  若股票比重低於目標 (如 50%)，可溫和加碼拉回長期目標 (如 60-70%)。
    * **提醒**：只做「提早佈局」而非賭 V 型反轉，避免高槓桿。
    """)

elif -1 <= final_score < 2: # 包含 -1 ~ +1.99
    st.info("### 🧘 正常區 (Score -1 ~ +1)")
    st.markdown("""
    * **狀態**：市場情緒與估值皆處於中性合理區間。
    * **資金操作**：
        1.  **照原定計畫定期定額**，不因短線波動亂調整。
        2.  每 6-12 個月檢查資產配置，做小幅再平衡即可。
    """)

elif -4 <= final_score < -1: # 包含 -4 ~ -1.01
    st.warning("### 🔥 偏熱區 (Score -1 ~ -4)")
    st.markdown("""
    * **狀態**：市場開始貪婪，風險升高。
    * **資金操作**：
        1.  **暫停所有主動加碼**，僅保留小額定期定額 (例如平常的 50%)。
        2.  檢視股票比重是否過高，可小幅獲利了結或轉入債券/現金。
        3.  逐步減碼槓桿產品。
    """)

else: # score < -4
    st.error("### 🚨 過熱自滿區 (Score < -4)")
    st.markdown("""
    * **狀態**：市場極度貪婪，估值昂貴，隨時可能反轉。
    * **資金操作**：
        1.  **不再新增股票部位**，新資金暫放現金。
        2.  **強力再平衡**：將股票部位調降回原先目標 (例如 80% → 60-70%)。
        3.  對高風險/高 Beta 個股進行風險刪減。
    """)

# 顯示計算公式詳情
with st.expander("查看詳細計算公式"):
    st.latex(r'''
    Score_{final} = \left[ \sum_{i=1}^{6} \left( \frac{Score_i}{2} \times Weight_i \right) \right] \times 8
    ''')
    st.write(f"本次計算: ( ({s1}/2 * 0.15) + ({s2}/2 * 0.15) + ({s3}/2 * 0.10) + ({s4}/2 * 0.15) + ({s5}/2 * 0.25) + ({s6}/2 * 0.20) ) * 8 = {final_score}")
