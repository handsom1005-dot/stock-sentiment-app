import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與排版
st.set_page_config(page_title="市場情緒量化儀表板 v3.0 (趨勢濾網版)", page_icon="📈", layout="wide")

st.title("📈 市場情緒量化儀表板 v3.0 (趨勢濾網版)")
st.markdown("依據 **「趨勢狀態」** 自動切換權重與計分標準，協助判斷「急殺進場」或「保守防禦」。")
st.markdown("---")

# ==========================================
# 1. 定義評分邏輯函數 (支援動態門檻)
# ==========================================

# 1. 恐懼貪婪 (通用標準)
def get_fg_score(value):
    # 0-25(+2), 26-44(+1), 45-55(0), 56-74(-1), 75-100(-2)
    if value <= 25: return 2
    elif value <= 44: return 1
    elif value <= 55: return 0
    elif value <= 74: return -1
    else: return -2

# 2. McClellan (通用標準)
def get_mcclellan_score(value):
    # <=-100(+2), -100~-50(+1), -50~+50(0), +50~+100(-1), >100(-2)
    if value <= -100: return 2
    elif value <= -50: return 1
    elif value <= 50: return 0
    elif value <= 100: return -1
    else: return -2

# 3. Put/Call (通用標準)
def get_pc_score(value):
    # >=1.0(+2), 0.8-0.99(+1), 0.6-0.79(0), 0.5-0.59(-1), <0.5(-2)
    if value >= 1.0: return 2
    elif value >= 0.8: return 1
    elif value >= 0.6: return 0
    elif value >= 0.5: return -1
    else: return -2

# [cite_start]4. VIX (動態標準) [cite: 156-161]
def get_vix_score(value, is_uptrend):
    if is_uptrend:
        # 上升趨勢 (Dip-buy): 對恐慌更敏感
        # >=35(+2), 25-34(+1), 15-24(0), 12-14(-1), <12(-2)
        if value >= 35: return 2
        elif value >= 25: return 1
        elif value >= 15: return 0
        elif value >= 12: return -1
        else: return -2
    else:
        # 非上升趨勢 (保守): 維持原標準
        # >=40(+2), 30-39(+1), 15-29(0), 12-14(-1), <12(-2)
        if value >= 40: return 2
        elif value >= 30: return 1
        elif value >= 15: return 0
        elif value >= 12: return -1
        else: return -2

# [cite_start]5. 200日乖離率 (動態標準) [cite: 149-155]
def get_bias_score(value, is_uptrend):
    if is_uptrend:
        # 上升趨勢 (Dip-buy): 回調不用太深即可視為便宜
        # <=-10%(+2), -10~-5%(+1), -5~+8%(0), +8~+12%(-1), >+12%(-2)
        if value <= -10: return 2
        elif value <= -5: return 1
        elif value <= 8: return 0
        elif value <= 12: return -1
        else: return -2
    else:
        # 非上升趨勢 (保守): 必須跌很深才給分
        # <=-20%(+2), -20~-10%(+1), -10~+10%(0), +10~+15%(-1), >+15%(-2)
        if value <= -20: return 2
        elif value <= -10: return 1
        elif value <= 10: return 0
        elif value <= 15: return -1
        else: return -2

# 6. Forward P/E (通用標準)
def get_pe_score(value):
    # <=15(+2), 15-18(+1), 18-22(0), 22-25(-1), >=25(-2)
    if value <= 15: return 2
    elif value < 18: return 1
    elif value <= 22: return 0
    elif value < 25: return -1
    else: return -2

# ==========================================
# 2. 自動抓取輔助數據
# ==========================================
try:
    vix_ticker = yf.Ticker("^VIX")
    vix_hist = vix_ticker.history(period="1d")
    default_vix = round(float(vix_hist['Close'].iloc[-1]), 2) if not vix_hist.empty else 15.0

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
# 3. 側邊欄：輸入數據
# ==========================================
st.sidebar.header("📊 輸入今日指標數據")

# 1. FGI
st.sidebar.markdown("### 1. 恐懼貪婪指數")
st.sidebar.markdown("[查詢連結](https://en.macromicro.me/charts/50108/cnn-fear-and-greed)")
in_fg = st.sidebar.number_input("輸入數值", value=50.00, step=0.01, format="%.2f")

# 2. McClellan
st.sidebar.markdown("### 2. McClellan Oscillator")
st.sidebar.markdown("[查詢連結](https://www.mcoscillator.com/market_breadth_data/)")
in_mcc = st.sidebar.number_input("輸入數值", value=0.000, step=0.001, format="%.3f")

# 3. Put/Call
st.sidebar.markdown("### 3. Put/Call Ratio")
st.sidebar.markdown("[查詢連結](https://en.macromicro.me/charts/449/us-cboe-options-put-call-ratio)")
in_pc = st.sidebar.number_input("輸入數值", value=0.65, step=0.01, format="%.2f")

# 4. VIX
st.sidebar.markdown("### 4. VIX 恐慌指數")
st.sidebar.markdown("[查詢連結](https://en.macromicro.me/series/355/vix)")
in_vix = st.sidebar.number_input("輸入數值", value=default_vix, step=0.1, format="%.2f")

# 5. 200日乖離率 (判斷趨勢的核心)
st.sidebar.markdown("### 5. S&P 500 200日乖離率")
st.sidebar.caption("若數值 > 0，視為上升趨勢；≤ 0 視為下行/盤整")
st.sidebar.markdown("[查詢連結](https://www.barchart.com/stocks/quotes/$SPX/technical-analysis)")
in_bias = st.sidebar.number_input("輸入百分比 (例如 5.00)", value=default_bias, step=0.1, format="%.2f")

# 6. Forward P/E
st.sidebar.markdown("### 6. Forward P/E Ratio")
st.sidebar.markdown("[查詢連結](https://en.macromicro.me/series/20052/sp500-forward-pe-ratio)")
in_pe = st.sidebar.number_input("輸入數值", value=20.0, step=0.1, format="%.2f")

# ==========================================
# [cite_start]4. 趨勢判斷與權重選擇 [cite: 132-147]
# ==========================================

# 趨勢判斷: 乖離率 > 0 代表價格在 200MA 之上 (Trend = True)
is_uptrend = in_bias > 0

if is_uptrend:
    trend_status = "🟢 上升趨勢 (Up Trend)"
    strategy_name = "🚀 急殺進場策略 (Dip-buy)"
    # 權重配置 (Dip-buy)
    w_vix = 0.25
    w_pc = 0.20
    w_mcc = 0.25
    w_fg = 0.10
    w_bias = 0.15
    w_pe = 0.05
else:
    trend_status = "🔴 下行/盤整趨勢 (Bear/Range)"
    strategy_name = "🛡️ 保守進場策略 (Defensive)"
    # 權重配置 (Bear/Range)
    w_bias = 0.30
    w_pe = 0.25
    w_mcc = 0.20
    w_vix = 0.15
    w_pc = 0.05
    w_fg = 0.05

# ==========================================
# 5. 計算核心邏輯
# ==========================================

# 取得得分 (VIX 和 Bias 傳入 is_uptrend 參數)
s1 = get_fg_score(in_fg)
s2 = get_mcclellan_score(in_mcc)
s3 = get_pc_score(in_pc)
s4 = get_vix_score(in_vix, is_uptrend)  # 動態
s5 = get_bias_score(in_bias, is_uptrend) # 動態
s6 = get_pe_score(in_pe)

# 加權總分計算
weighted_sum = (
    (s1/2 * w_fg) + 
    (s2/2 * w_mcc) + 
    (s3/2 * w_pc) +
    (s4/2 * w_vix) + 
    (s5/2 * w_bias) + 
    (s6/2 * w_pe)
)
final_score = round(weighted_sum * 8, 2)

# ==========================================
# 6. 主畫面顯示
# ==========================================
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("趨勢狀態判定")
    if is_uptrend:
        st.success(f"**{trend_status}**")
        st.caption("條件：S&P 500 > 200 DMA (乖離率 > 0)")
    else:
        st.error(f"**{trend_status}**")
        st.caption("條件：S&P 500 ≤ 200 DMA (乖離率 ≤ 0)")
    
    st.markdown(f"**目前採用：{strategy_name}**")
    st.markdown("---")
    
    # 分數顯示
    st.metric(label="綜合市場情緒分數", value=f"{final_score} 分")
    
    status_label = ""
    if final_score >= 5: status_label = "💥 極度恐慌區 (強烈買進)"
    elif final_score >= 2: status_label = "😨 恐慌區 (分批買進)"
    elif final_score >= -1: status_label = "☁️ 正常區 (定期定額)"
    elif final_score >= -4: status_label = "🔥 偏熱區 (暫停加碼)"
    else: status_label = "🚨 過熱自滿區 (風險控管)"
    
    st.info(f"建議動作：**{status_label}**")

with col2:
    st.markdown("#### 📊 指標得分與權重詳情")
    
    # 建立表格數據
    metrics_data = {
        "指標": ["(1) 恐懼貪婪", "(2) McClellan", "(3) Put/Call", "(4) VIX", "(5) 200日乖離", "(6) Forward P/E"],
        "輸入值": [
            f"{in_fg:.2f}", 
            f"{in_mcc:.3f}", 
            f"{in_pc:.2f}", 
            f"{in_vix:.2f}", 
            f"{in_bias:.2f}%", 
            f"{in_pe:.2f}"
        ],
        "得分 (-2~+2)": [s1, s2, s3, s4, s5, s6],
        "目前權重": [
            f"{int(w_fg*100)}%", 
            f"{int(w_mcc*100)}%", 
            f"{int(w_pc*100)}%", 
            f"{int(w_vix*100)}%", 
            f"{int(w_bias*100)}%", 
            f"{int(w_pe*100)}%"
        ]
    }
    
    df = pd.DataFrame(metrics_data)
    # 標示出權重較高的項目
    st.dataframe(df, hide_index=True, use_container_width=True)
    
    if is_uptrend:
        st.caption("💡 **Dip-buy 模式**：VIX、McClellan 與 Put/Call 權重加重，捕捉急殺機會。")
    else:
        st.caption("🛡️ **保守模式**：大幅加重 200日乖離與 P/E 權重，防止在空頭市場接刀。")

st.markdown("---")

# ==========================================
# [cite_start]7. 投資操作建議 (維持五區間) [cite: 162-173]
# ==========================================
st.header("💡 投資操作建議")

if final_score >= 5:
    st.success("### 💎 極度恐慌區 (Score ≥ +5)")
    st.markdown("""
    * **操作**：啟動「積極分批買入」。
    * **資金**：當期投入 **1.5～2 倍** (分 3-6 批)。
    * **備註**：機會難得，但需嚴控槓桿。
    """)
elif 2 <= final_score < 5:
    st.success("### 💰 恐慌區 (Score +2 ~ +4)")
    st.markdown("""
    * **操作**：進入「加碼區」。
    * **資金**：當期投入 **1.2～1.5 倍** (分 2-4 批)。
    * **備註**：適合溫和加碼，拉回長期部位目標。
    """)
elif -1 <= final_score < 2:
    st.info("### 🧘 正常區 (Score -1 ~ +1)")
    st.markdown("""
    * **操作**：**按原定計畫定期定額**。
    * **資金**：不調整，不因短線波動改變節奏。
    """)
elif -4 <= final_score < -1:
    st.warning("### 🔥 偏熱區 (Score -1 ~ -4)")
    st.markdown("""
    * **操作**：**暫停主動加碼**，偏向再平衡。
    * **資金**：僅保留小額扣款或暫停扣款。
    """)
else:
    st.error("### 🚨 過熱自滿區 (Score < -4)")
    st.markdown("""
    * **操作**：**不新增股票部位**。
    * **資金**：回到目標股債比，必要時分批減碼獲利了結。
    """)

# ==========================================
# 8. 顯示給分標準表 (支援動態 Tabs)
# ==========================================
st.markdown("---")
with st.expander("📖 查看目前適用的給分標準 (點擊展開)", expanded=False):
    
    tab_current, tab_other = st.tabs([f"目前模式: {strategy_name}", "另一模式對照"])
    
    # 定義顯示函數以減少重複代碼
    def show_rules(uptrend_mode):
        st.markdown(f"#### 📊 適用權重與門檻 ({'上升趨勢 Dip-buy' if uptrend_mode else '非上升趨勢 Conservative'})")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**1. VIX 恐慌指數**")
            if uptrend_mode:
                st.markdown("""
                | 數值 | 分數 |
                | :--- | :---: |
                | **≥ 35** | +2 |
                | **25 – 34** | +1 |
                | **15 – 24** | 0 |
                | **12 – 14** | -1 |
                | **< 12** | -2 |
                """)
                st.caption("⚡ Dip-buy 特徵：對恐慌更敏感 (門檻由 40 降至 35)")
            else:
                st.markdown("""
                | 數值 | 分數 |
                | :--- | :---: |
                | **≥ 40** | +2 |
                | **30 – 39** | +1 |
                | **15 – 29** | 0 |
                | **12 – 14** | -1 |
                | **< 12** | -2 |
                """)
                st.caption("🛡️ 保守特徵：需極端恐慌才給高分")

        with col_b:
            st.markdown("**2. 200日乖離率 (Bias)**")
            if uptrend_mode:
                st.markdown("""
                | 數值 | 分數 |
                | :--- | :---: |
                | **≤ -10%** | +2 |
                | **-10% ~ -5%** | +1 |
                | **-5% ~ +8%** | 0 |
                | **+8% ~ +12%** | -1 |
                | **> +12%** | -2 |
                """)
                st.caption("⚡ Dip-buy 特徵：回調 5-10% 即視為買點")
            else:
                st.markdown("""
                | 數值 | 分數 |
                | :--- | :---: |
                | **≤ -20%** | +2 |
                | **-20% ~ -10%** | +1 |
                | **-10% ~ +10%** | 0 |
                | **+10% ~ +15%** | -1 |
                | **> +15%** | -2 |
                """)
                st.caption("🛡️ 保守特徵：需跌深 (20%) 才視為底部")
        
        st.markdown("---")
        st.markdown("**其餘指標標準 (通用)**")
        st.markdown("""
        * **恐懼貪婪**: ≤25(+2), 26-44(+1), 45-55(0), 56-74(-1), ≥75(-2)
        * **McClellan**: ≤-100(+2), -100~-50(+1), -50~50(0), 50~100(-1), >100(-2)
        * **Put/Call**: ≥1.0(+2), 0.8-0.99(+1), 0.6-0.79(0), 0.5-0.59(-1), <0.5(-2)
        * **Forward P/E**: ≤15(+2), 15-18(+1), 18-22(0), 22-25(-1), ≥25(-2)
        """)

    with tab_current:
        show_rules(is_uptrend)
    
    with tab_other:
        show_rules(not is_uptrend)
