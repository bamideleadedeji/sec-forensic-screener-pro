"""
SEC 10-K Financial Red-Flag, Altman Z-Score & Piotroski F-Score Screener (v2.0)
100% Real US SEC EDGAR XBRL Filings + Custom Financial Statement Uploader
"""

import io
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import plotly.express as px
from sec_edgar_client import COMPANY_CIKS, fetch_sec_10k_metrics
from forensic_scoring_engine import compute_forensic_scores

st.set_page_config(page_title="SEC 10-K Forensic & Altman Z-Score Screener", page_icon="📑", layout="wide")
st.title("📑 SEC 10-K Financial Red-Flag, Altman Z-Score & Piotroski F-Score Screener")
st.caption("Live US SEC EDGAR XBRL 10-K Ingestion • Altman Z-Score Bankruptcy Risk • Piotroski F-Score (0–9) • Beneish M-Score Earnings Quality")
st.divider()

DEFAULT_MCAPS = {
    "AAPL (Apple Inc.)": 3500.0,
    "MSFT (Microsoft Corp.)": 3100.0,
    "NVDA (NVIDIA Corp.)": 3400.0,
    "AMZN (Amazon.com Inc.)": 2200.0,
    "TSLA (Tesla Inc.)": 1050.0,
    "GOOGL (Alphabet Inc.)": 2100.0,
    "WMT (Walmart Inc.)": 720.0,
    "BA (The Boeing Company)": 115.0,
}

source_mode = st.sidebar.radio("Data Source", ["Live US SEC EDGAR 10-K API", "Upload Custom Company CSV / Excel"])

try:
    if source_mode == "Live US SEC EDGAR 10-K API":
        selected_company = st.sidebar.selectbox("Select Public US Issuer (SEC EDGAR)", list(COMPANY_CIKS.keys()))
        default_mcap = DEFAULT_MCAPS.get(selected_company, 250.0)
        market_cap_bn = st.sidebar.number_input("Company Market Cap ($ Billions USD)", min_value=0.05, max_value=5000.0, value=default_mcap, step=10.0)
        custom_cik = st.sidebar.text_input("Or Enter Any 10-Digit SEC CIK (Optional)", value="")
        target_cik = custom_cik.strip() if custom_cik.strip() else COMPANY_CIKS[selected_company]
        issuer_label = f"CIK {target_cik.zfill(10)}" if custom_cik.strip() else selected_company
        with st.spinner(f"Streaming audited 10-K XBRL statements from SEC EDGAR for {issuer_label}..."):
            fin_df = fetch_sec_10k_metrics(target_cik)
    else:
        issuer_label = "Custom Uploaded Financials"
        market_cap_bn = st.sidebar.number_input("Company Market Cap ($ Billions USD)", min_value=0.05, max_value=5000.0, value=250.0, step=10.0)
        uploaded = st.sidebar.file_uploader("Upload Multi-Year Financial Statements (.csv or .xlsx)", type=["csv", "xlsx"])
        if not uploaded:
            st.info("Upload a multi-year CSV/Excel ledger or switch to 'Live US SEC EDGAR 10-K API' in the sidebar.")
            st.stop()
        fin_df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)

    scores = compute_forensic_scores(fin_df, market_cap_usd=market_cap_bn * 1e9)
except Exception as exc:
    st.error(f"Data Ingestion / Scoring Error: {exc}")
    st.stop()

st.subheader(f"Executive Forensic & Credit Scorecard — {issuer_label} (FY {scores['fiscal_year']})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Altman Z-Score", f"{scores['altman_z']:.2f}", delta=scores["z_zone"])
c2.metric("Piotroski F-Score", f"{scores['piotroski_f']} / 9", delta=scores["f_grade"])
c3.metric("Beneish M-Score", f"{scores['beneish_m']:.2f}", delta=scores["m_flag"])
c4.metric("Return on Assets (ROA)", f"{scores['roa_pct']:.2f}%", delta=f"Gross Margin: {scores['gross_margin_pct']:.2f}%")

tab1, tab2, tab3 = st.tabs(["📊 Piotroski 9-Point Breakdown", "📈 Multi-Year 10-K Financials", "📥 Executive Excel & Memo Export"])

with tab1:
    sig_df = pd.DataFrame([{"Criterion": k, "Passed (1=Yes, 0=No)": v} for k, v in scores["f_signals"].items()])
    st.dataframe(sig_df, width="stretch")
    st.plotly_chart(px.bar(fin_df, x="Fiscal_Year", y=["Revenue", "OperatingIncome", "NetIncome", "OperatingCashFlow"], barmode="group", title=f"{issuer_label} — Audited 10-K Revenue, Earnings & Operating Cash Flow ($)"), width="stretch")

with tab2:
    st.dataframe(fin_df, width="stretch")

with tab3:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([
            {"Metric": "Issuer", "Value": issuer_label},
            {"Metric": "Latest Fiscal Year", "Value": scores["fiscal_year"]},
            {"Metric": "Altman Z-Score", "Value": f"{scores['altman_z']:.2f} ({scores['z_zone']})"},
            {"Metric": "Piotroski F-Score", "Value": f"{scores['piotroski_f']}/9 ({scores['f_grade']})"},
            {"Metric": "Beneish M-Score", "Value": f"{scores['beneish_m']:.2f} ({scores['m_flag']})"},
            {"Metric": "ROA (%)", "Value": f"{scores['roa_pct']:.2f}%"},
            {"Metric": "Current Ratio", "Value": f"{scores['current_ratio']:.2f}x"},
        ]).to_excel(writer, sheet_name="01_Forensic_Scorecard", index=False)
        fin_df.to_excel(writer, sheet_name="02_Audited_10K_Statements", index=False)
        sig_df.to_excel(writer, sheet_name="03_Piotroski_F_Signals", index=False)

    memo_text = (
        f"INSTITUTIONAL 10-K FORENSIC & CREDIT SCREENING MEMORANDUM\n"
        f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Issuer: {issuer_label} | Fiscal Year: {scores['fiscal_year']}\n"
        f"------------------------------------------------------------\n"
        f"1. Altman Z-Score : {scores['altman_z']:.2f} -> {scores['z_zone']}\n"
        f"2. Piotroski F    : {scores['piotroski_f']}/9 -> {scores['f_grade']}\n"
        f"3. Beneish M-Score: {scores['beneish_m']:.2f} -> {scores['m_flag']}\n"
        f"4. Accruals/Assets: {scores['accruals_to_assets_pct']:.2f}% | Current Ratio: {scores['current_ratio']:.2f}x\n"
    )
    d1, d2 = st.columns(2)
    d1.download_button("📊 Download Multi-Sheet Excel Forensic Report (.xlsx)", buf.getvalue(), "SEC_10K_Forensic_Scorecard.xlsx")
    d2.download_button("📄 Download Executive Credit & Forensic Memo (.txt)", memo_text, "SEC_10K_Forensic_Memo.txt")
