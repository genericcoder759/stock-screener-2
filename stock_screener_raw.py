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
st.markdown("Step 1: Collect and Review Raw Data from SEC & Yahoo Finance")

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
# SEC EDGAR DATA RETRIEVAL
# ============================================================================

def get_sec_filings_metadata(ticker):
    """Get SEC filing metadata for a ticker"""
    try:
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=exclude&count=1&output=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'filings' in data and data['filings'].get('filings'):
                filing = data['filings']['filings'][0]
                return {
                    'filing_date': filing.get('filingDate', None),
                    'accession_number': filing.get('accessionNumber', None),
                    'status': '✅ Found'
                }
        return {'filing_date': None, 'accession_number': None, 'status': '❌ Not Found'}
    except Exception as e:
        return {'filing_date': None, 'accession_number': None, 'status': f'⚠️ Error: {str(e)[:30]}'}

def get_sec_financial_data(ticker, cik=None):
    """
    Fetch SEC 10-K financial data via SEC EDGAR JSON API
    Returns raw financial statement data
    """
    raw_data = {
        # Balance Sheet
        'total_assets': None,
        'total_liabilities': None,
        'total_equity': None,
        'total_debt_short_term': None,
        'total_debt_long_term': None,
        'cash': None,
        
        # Income Statement
        'revenue': None,
        'revenue_prior_year': None,
        'cogs': None,
        'gross_profit': None,
        'net_income': None,
        'net_income_prior_year': None,
        'eps_current': None,
        'eps_prior_year': None,
        
        # Cash Flow
        'operating_cash_flow': None,
        'capex': None,
        'net_debt_issued': None,
        'interest_paid': None,
        
        # Filing Info
        'filing_date': None,
        'sec_status': None
    }
    
    try:
        # Get filing metadata
        filing_meta = get_sec_filings_metadata(ticker)
        raw_data['filing_date'] = filing_meta['filing_date']
        raw_data['sec_status'] = filing_meta['status']
        
        if filing_meta['status'] != '✅ Found':
            return raw_data
        
        # Try to get CIK
        if not cik:
            try:
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={ticker}&action=getcompany&output=json"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    cik = resp.json()['cik_str']
            except:
                pass
        
        # Fetch 10-K data from SEC Edgar JSON API
        if cik:
            # This is a simplified approach - SEC EDGAR JSON API requires CIK
            # In production, you'd parse the actual 10-K filing XML
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}/us-gaap/Assets.json"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Extract latest 10-K values (this is simplified)
                    if 'units' in data and 'USD' in data['units']:
                        filings = data['units']['USD']
                        if filings:
                            latest = filings[-1]
                            raw_data['total_assets'] = latest.get('val')
            except:
                pass
        
        # Note: Full SEC data extraction requires parsing XML filings
        # For now, we'll mark these as "SEC: Requires Full Parse"
        raw_data['sec_status'] = f"{filing_meta['status']} | Filing: {filing_meta['filing_date']}"
        
        return raw_data
    
    except Exception as e:
        raw_data['sec_status'] = f"⚠️ Error: {str(e)[:50]}"
        return raw_data

# ============================================================================
# YAHOO FINANCE DATA RETRIEVAL
# ============================================================================

def get_yahoo_finance_data(ticker):
    """Fetch raw Yahoo Finance data"""
    raw_data = {
        # Price Data
        'current_price': None,
        'market_cap': None,
        'shares_outstanding': None,
        
        # Valuation
        'trailing_pe': None,
        'eps_ttm': None,
        'eps_trailing': None,
        'dividend_yield': None,
        'book_value': None,
        'pb_ratio': None,
        
        # Margins & Returns
        'gross_margin': None,
        'net_margin': None,
        'roa': None,
        'roe': None,
        
        # Growth
        'revenue_ttm': None,
        'net_income_ttm': None,
        
        # Debt
        'total_debt': None,
        'net_debt': None,
        'debt_to_equity': None,
        
        # Technical
        'price_52w_high': None,
        'price_52w_low': None,
        'avg_volume': None,
        
        # Time Series (for calculations)
        'daily_closes': None,
        'historical_data': None,
        
        'status': None
    }
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        # Price Data
        raw_data['current_price'] = info.get('currentPrice') or hist['Close'].iloc[-1]
        raw_data['market_cap'] = info.get('marketCap')
        raw_data['shares_outstanding'] = info.get('sharesOutstanding')
        
        # Valuation
        raw_data['trailing_pe'] = info.get('trailingPE')
        raw_data['eps_ttm'] = info.get('trailingEps')
        raw_data['eps_trailing'] = info.get('epsTrailingTwelveMonths')
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
        raw_data['net_debt'] = info.get('netDebtToEbitda')
        raw_data['debt_to_equity'] = info.get('debtToEquity')
        
        # Technical
        raw_data['price_52w_high'] = info.get('fiftyTwoWeekHigh')
        raw_data['price_52w_low'] = info.get('fiftyTwoWeekLow')
        raw_data['avg_volume'] = info.get('averageVolume')
        
        # Historical for technical calculations
        raw_data['daily_closes'] = hist['Close'].values if not hist.empty else None
        raw_data['historical_data'] = hist if not hist.empty else None
        
        raw_data['status'] = '✅ Success'
        
        return raw_data
    
    except Exception as e:
        raw_data['status'] = f"❌ Error: {str(e)}"
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
    # Handle both newline and comma-separated
    lines = stock_list.strip().split('\n')
    for line in lines:
        line_tickers = [t.strip().upper() for t in line.split(',')]
        tickers.extend([t for t in line_tickers if t])
    tickers = list(set(tickers))  # Remove duplicates
else:
    tickers = []

st.info(f"📌 Found {len(tickers)} ticker(s): {', '.join(tickers)}")

st.divider()

# Data collection
st.subheader("2️⃣ Collect Raw Data")

if st.button("🔄 Fetch Raw Data from SEC & Yahoo", use_container_width=True):
    if not tickers:
        st.error("Please enter at least one ticker symbol")
    else:
        progress_bar = st.progress(0)
        status_container = st.container()
        
        all_raw_data = []
        
        for idx, ticker in enumerate(tickers):
            with status_container:
                st.info(f"Fetching {ticker} ({idx+1}/{len(tickers)})")
            
            progress = (idx + 1) / len(tickers)
            progress_bar.progress(progress)
            
            # Fetch SEC data
            sec_data = get_sec_financial_data(ticker)
            
            # Fetch Yahoo data
            yahoo_data = get_yahoo_finance_data(ticker)
            
            # Combine raw data
            raw_entry = {
                'Ticker': ticker,
                
                # SEC Data Status
                'SEC_Filing_Date': sec_data['filing_date'],
                'SEC_Status': sec_data['sec_status'],
                
                # Yahoo Status
                'Yahoo_Status': yahoo_data['status'],
                'Yahoo_Price': yahoo_data['current_price'],
                
                # SEC Raw (Balance Sheet)
                'SEC_Total_Assets': sec_data['total_assets'],
                'SEC_Total_Liabilities': sec_data['total_liabilities'],
                'SEC_Total_Equity': sec_data['total_equity'],
                'SEC_Total_Debt_ST': sec_data['total_debt_short_term'],
                'SEC_Total_Debt_LT': sec_data['total_debt_long_term'],
                'SEC_Cash': sec_data['cash'],
                
                # SEC Raw (Income Statement)
                'SEC_Revenue_Current': sec_data['revenue'],
                'SEC_Revenue_Prior': sec_data['revenue_prior_year'],
                'SEC_COGS': sec_data['cogs'],
                'SEC_Gross_Profit': sec_data['gross_profit'],
                'SEC_Net_Income_Current': sec_data['net_income'],
                'SEC_Net_Income_Prior': sec_data['net_income_prior_year'],
                'SEC_EPS_Current': sec_data['eps_current'],
                'SEC_EPS_Prior': sec_data['eps_prior_year'],
                
                # SEC Raw (Cash Flow)
                'SEC_Operating_CF': sec_data['operating_cash_flow'],
                'SEC_CapEx': sec_data['capex'],
                'SEC_Net_Debt_Issued': sec_data['net_debt_issued'],
                'SEC_Interest_Paid': sec_data['interest_paid'],
                
                # Yahoo Raw (Valuation)
                'Yahoo_Market_Cap': yahoo_data['market_cap'],
                'Yahoo_Shares_Out': yahoo_data['shares_outstanding'],
                'Yahoo_P/E_Trailing': yahoo_data['trailing_pe'],
                'Yahoo_EPS_TTM': yahoo_data['eps_ttm'],
                'Yahoo_EPS_Trailing': yahoo_data['eps_trailing'],
                'Yahoo_Dividend_Yield': yahoo_data['dividend_yield'],
                'Yahoo_Book_Value': yahoo_data['book_value'],
                'Yahoo_P/B': yahoo_data['pb_ratio'],
                
                # Yahoo Raw (Margins & Returns)
                'Yahoo_Gross_Margin': yahoo_data['gross_margin'],
                'Yahoo_Net_Margin': yahoo_data['net_margin'],
                'Yahoo_ROA': yahoo_data['roa'],
                'Yahoo_ROE': yahoo_data['roe'],
                
                # Yahoo Raw (Growth)
                'Yahoo_Revenue_TTM': yahoo_data['revenue_ttm'],
                'Yahoo_Net_Income_TTM': yahoo_data['net_income_ttm'],
                
                # Yahoo Raw (Debt)
                'Yahoo_Total_Debt': yahoo_data['total_debt'],
                'Yahoo_Net_Debt': yahoo_data['net_debt'],
                'Yahoo_D/E_Ratio': yahoo_data['debt_to_equity'],
                
                # Yahoo Raw (Technical)
                'Yahoo_52W_High': yahoo_data['price_52w_high'],
                'Yahoo_52W_Low': yahoo_data['price_52w_low'],
                'Yahoo_Avg_Volume': yahoo_data['avg_volume'],
                'Yahoo_Daily_Closes_Available': yahoo_data['daily_closes'] is not None,
            }
            
            all_raw_data.append(raw_entry)
        
        progress_bar.empty()
        
        # Display consolidated raw data table
        st.divider()
        st.subheader("3️⃣ Consolidated Raw Data")
        
        if all_raw_data:
            df_raw = pd.DataFrame(all_raw_data)
            
            # Display full table
            st.dataframe(df_raw, use_container_width=True, height=400)
            
            # Summary statistics
            st.subheader("📊 Data Availability Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Tickers", len(tickers))
            
            with col2:
                sec_available = sum(1 for ticker in tickers if df_raw[df_raw['Ticker']==ticker]['SEC_Status'].values[0] == '✅ Found')
                st.metric("SEC Filings Found", sec_available)
            
            with col3:
                yahoo_available = sum(1 for ticker in tickers if df_raw[df_raw['Ticker']==ticker]['Yahoo_Status'].values[0] == '✅ Success')
                st.metric("Yahoo Data Retrieved", yahoo_available)
            
            # Download raw data
            st.divider()
            csv = df_raw.to_csv(index=False)
            st.download_button(
                label="📥 Download Raw Data (CSV)",
                data=csv,
                file_name=f"raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success("✅ Raw data collection complete. Review the table above for data availability.")
        else:
            st.error("No data retrieved")

st.divider()
st.markdown("""
---
**Next Steps:**
1. ✅ Review raw data collection above
2. ⏳ Validate data sources (SEC vs Yahoo)
3. ⏳ Create metric calculation formulas
4. ⏳ Run calculations on collected data
""")
