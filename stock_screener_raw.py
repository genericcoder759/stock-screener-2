import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Stock Screener - Raw Data", layout="wide")
st.title("📊 Stock Screener - Raw Data Collection")
st.markdown("Fetch Yahoo Finance + SEC 10-K Data for your tickers")

# ============================================================================
# CONFIGURATION
# ============================================================================

DEFINITIONS = {
    'Levered_FCF': 'CFO - CapEx - Net Debt Repayment',
    'EPS_Growth': '(EPS_TTM / EPS_prior_year_TTM) - 1',
    'CROIC': 'FCF / (Total Debt + Total Equity - Cash)',
    'Risk_Free_Rate': '4.5%',
    'MA_200': 'Daily closing prices'
}

# ============================================================================
# SEC FILING DATA RETRIEVAL (ON-DEMAND ONLY)
# ============================================================================

def get_sec_filing_info(ticker):
    """Fetch ONLY SEC 10-K metadata (fast, minimal parsing)"""
    sec_data = {
        'sec_filing_date': None,
        'sec_status': None,
    }
    
    try:
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=exclude&count=1&output=json"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'filings' in data and data['filings'].get('filings'):
                filing = data['filings']['filings'][0]
                sec_data['sec_filing_date'] = filing.get('filingDate', None)
                sec_data['sec_status'] = '✅ Found'
            else:
                sec_data['sec_status'] = '❌ Not found'
        else:
            sec_data['sec_status'] = '⚠️ SEC unavailable'
    except Exception as e:
        sec_data['sec_status'] = f'⚠️ Timeout'
    
    return sec_data

# ============================================================================
# YAHOO FINANCE DATA RETRIEVAL (FAST)
# ============================================================================

def get_yahoo_finance_data(ticker):
    """Fetch raw Yahoo Finance data - OPTIMIZED FOR SPEED"""
    raw_data = {
        'ticker': ticker,
        'yahoo_status': None,
        'current_price': None,
        'market_cap': None,
        'shares_outstanding': None,
        'trailing_pe': None,
        'eps_ttm': None,
        'dividend_yield': None,
        'book_value': None,
        'pb_ratio': None,
        'gross_margin': None,
        'net_margin': None,
        'roa': None,
        'roe': None,
        'revenue_ttm': None,
        'net_income_ttm': None,
        'total_debt': None,
        'debt_to_equity': None,
        'price_52w_high': None,
        'price_52w_low': None,
        'avg_volume': None,
        'daily_closes_available': False,
    }
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        # Price Data
        raw_data['current_price'] = info.get('currentPrice') or (hist['Close'].iloc[-1] if not hist.empty else None)
        raw_data['market_cap'] = info.get('marketCap')
        raw_data['shares_outstanding'] = info.get('sharesOutstanding')
        
        # Valuation
        raw_data['trailing_pe'] = info.get('trailingPE')
        raw_data['eps_ttm'] = info.get('trailingEps')
        raw_data['dividend_yield'] = info.get('dividendYield')
        raw_data['book_value'] = info.get('bookValue')
        raw_data['pb_ratio'] = info.get('priceToBook')
        
        # Margins & Returns
        raw_data['gross_margin'] = info.get('grossMargins')
        raw_data['net_margin'] = info.get('profitMargins')
        raw_data['roa'] = info.get('returnOnAssets')
        raw_data['roe'] = info.get('returnOnEquity')
        
        # Growth
        raw_data['revenue_ttm'] = info.get('totalRevenue')
        raw_data['net_income_ttm'] = info.get('netIncomeToCommon')
        
        # Debt
        raw_data['total_debt'] = info.get('totalDebt')
        raw_data['debt_to_equity'] = info.get('debtToEquity')
        
        # Technical
        raw_data['price_52w_high'] = info.get('fiftyTwoWeekHigh')
        raw_data['price_52w_low'] = info.get('fiftyTwoWeekLow')
        raw_data['avg_volume'] = info.get('averageVolume')
        raw_data['daily_closes_available'] = not hist.empty
        
        raw_data['yahoo_status'] = '✅ Success'
        
        return raw_data
    
    except Exception as e:
        raw_data['yahoo_status'] = f"❌ Error: {str(e)[:30]}"
        return raw_data

# ============================================================================
# MAIN APP
# ============================================================================

st.sidebar.header("📋 Configuration")
st.sidebar.markdown("**Metric Definitions:**")
for key, value in DEFINITIONS.items():
    st.sidebar.text(f"{key}: {value}")

st.divider()

# Input: Stock list
st.subheader("1️⃣ Enter Stock Tickers")
stock_list = st.text_area(
    "Enter tickers (one per line or comma-separated):",
    value="AAPL\nMSFT\nGOOGL",
    height=100,
    help="One ticker per line, or comma-separated"
)

# Parse tickers
if stock_list:
    tickers = []
    lines = stock_list.strip().split('\n')
    for line in lines:
        line_tickers = [t.strip().upper() for t in line.split(',')]
        tickers.extend([t for t in line_tickers if t])
    tickers = list(set(tickers))
else:
    tickers = []

st.info(f"📌 Found {len(tickers)} ticker(s): {', '.join(tickers)}")

st.divider()

# Data collection
st.subheader("2️⃣ Fetch Data")

if st.button("⚡ Fetch Data Now (Yahoo + SEC)", use_container_width=True):
    if not tickers:
        st.error("Please enter at least one ticker symbol")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_raw_data = []
        
        for idx, ticker in enumerate(tickers):
            status_text.text(f"Fetching {ticker}... ({idx+1}/{len(tickers)})")
            progress = (idx + 1) / len(tickers)
            progress_bar.progress(progress)
            
            # Always fetch Yahoo data (fast)
            yahoo_data = get_yahoo_finance_data(ticker)
            
            # Always fetch SEC data (only when button clicked)
            sec_data = get_sec_filing_info(ticker)
            yahoo_data.update(sec_data)
            
            all_raw_data.append(yahoo_data)
        
        progress_bar.empty()
        status_text.empty()
        
        # Display consolidated raw data table
        st.divider()
        st.subheader("3️⃣ Raw Data Collection Results")
        
        if all_raw_data:
            df_raw = pd.DataFrame(all_raw_data)
            
            # Reorder columns for clarity
            column_order = [
                'ticker',
                'yahoo_status',
                'sec_status',
                'sec_filing_date',
                'current_price',
                'market_cap',
                'shares_outstanding',
                'trailing_pe',
                'eps_ttm',
                'dividend_yield',
                'book_value',
                'pb_ratio',
                'gross_margin',
                'net_margin',
                'roa',
                'roe',
                'revenue_ttm',
                'net_income_ttm',
                'total_debt',
                'debt_to_equity',
                'price_52w_high',
                'price_52w_low',
                'avg_volume',
                'daily_closes_available',
            ]
            
            df_raw = df_raw[column_order]
            
            # Display full table
            st.dataframe(df_raw, use_container_width=True, height=400)
            
            # Summary statistics
            st.subheader("📊 Data Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Tickers", len(tickers))
            
            with col2:
                successful_yahoo = sum(1 for s in df_raw['yahoo_status'] if '✅' in s)
                st.metric("Yahoo Success", successful_yahoo)
            
            with col3:
                successful_sec = sum(1 for s in df_raw['sec_status'] if '✅' in s)
                st.metric("SEC Found", successful_sec)
            
            # Download raw data
            st.divider()
            csv = df_raw.to_csv(index=False)
            st.download_button(
                label="📥 Download Raw Data (CSV)",
                data=csv,
                file_name=f"raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success("✅ Data collection complete!")
            
            # Show which data is available
            st.divider()
            st.markdown("### ✅ Data Collected")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("**Yahoo Finance:**")
                st.markdown("""
                ✅ Stock Price & Market Cap
                ✅ P/E Ratio & EPS (TTM)
                ✅ Valuation Metrics (P/B, Div Yield)
                ✅ Profitability (Margins, ROA, ROE)
                ✅ Revenue & Net Income (TTM)
                ✅ Debt Metrics
                ✅ Technical Data (52W High/Low)
                ✅ Daily Closing Prices
                """)
            
            with col_right:
                st.markdown("**SEC 10-K Filings:**")
                st.markdown("""
                ✅ Latest Filing Date
                ✅ Filing Status
                
                **Ready for Phase 2:**
                - Full SEC XML parsing
                - Balance sheet (Assets, Liabilities, Equity)
                - Income statement (Revenue, Net Income)
                - Cash flow (Operating CF, CapEx)
                - Debt details (ST/LT debt, interest paid)
                """)
        else:
            st.error("No data retrieved")

st.divider()
st.markdown("""
---
**Workflow:**
1. ✅ Enter tickers (nothing fetches yet)
2. ✅ Click button → Fetches Yahoo + SEC automatically
3. ✅ See all raw data in table
4. ⏳ Next: Calculate your 16 metrics
""")
