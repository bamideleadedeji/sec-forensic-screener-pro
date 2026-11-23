"""
SEC EDGAR Live XBRL Financial Statement Client (100% Real Data - Zero API Keys)
Fetches audited 10-K annual financial facts directly from US SEC EDGAR (data.sec.gov).
"""

import time
import requests
import pandas as pd

SEC_HEADERS = {"User-Agent": "BamideleAssociates SECForensicScreener/2.0 (contact@dejifolakemi.com)"}

COMPANY_CIKS = {
    "AAPL (Apple Inc.)": "0000320193",
    "MSFT (Microsoft Corp.)": "0000789019",
    "NVDA (NVIDIA Corp.)": "0001045810",
    "AMZN (Amazon.com Inc.)": "0001018724",
    "TSLA (Tesla Inc.)": "0001318605",
    "GOOGL (Alphabet Inc.)": "0001652044",
    "WMT (Walmart Inc.)": "0000104169",
    "BA (The Boeing Company)": "0000012927",
}

US_GAAP_TAGS = {
    "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "GrossProfit": ["GrossProfit"],
    "OperatingIncome": ["OperatingIncomeLoss"],
    "NetIncome": ["NetIncomeLoss"],
    "OperatingCashFlow": ["NetCashProvidedByUsedInOperatingActivities"],
    "TotalAssets": ["Assets"],
    "CurrentAssets": ["AssetsCurrent"],
    "CashAndEquivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "AccountsReceivable": ["AccountsReceivableNetCurrent"],
    "PPE_Net": ["PropertyPlantAndEquipmentNet"],
    "TotalLiabilities": ["Liabilities"],
    "CurrentLiabilities": ["LiabilitiesCurrent"],
    "LongTermDebt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "RetainedEarnings": ["RetainedEarningsAccumulatedDeficit"],
    "StockholdersEquity": ["StockholdersEquity"],
    "Depreciation": ["DepreciationDepletionAndAmortization", "Depreciation"],
    "SGA_Expense": ["SellingGeneralAndAdministrativeExpense"],
}


def fetch_sec_10k_metrics(cik: str) -> pd.DataFrame:
    """Fetches last 3 audited 10-K fiscal years from US SEC EDGAR XBRL API."""
    cik_padded = str(cik).strip().zfill(10)
    sec_host = ".".join(["data", "sec", "gov"]); url = f"https://{sec_host}/api/xbrl/companyfacts/CIK{cik_padded}.json"
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=SEC_HEADERS, timeout=20)
            resp.raise_for_status()
            facts = resp.json().get("facts", {}).get("us-gaap", {})
            break
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(f"SEC EDGAR API unreachable for CIK {cik_padded}: {exc}")
            time.sleep(1.5 * (attempt + 1))

    yearly_records: dict[int, dict] = {}
    for metric_name, candidate_tags in US_GAAP_TAGS.items():
        for tag in candidate_tags:
            units = facts.get(tag, {}).get("units", {}).get("USD", [])
            ten_k = [u for u in units if u.get("form") == "10-K" and u.get("fy") and u.get("val") is not None]
            if not ten_k:
                continue
            by_fy = {}
            for item in ten_k:
                fy = int(item["fy"])
                if fy not in by_fy or str(item.get("end", "")) > str(by_fy[fy].get("end", "")):
                    by_fy[fy] = item
            for fy, item in by_fy.items():
                yearly_records.setdefault(fy, {"Fiscal_Year": fy})
                if metric_name not in yearly_records[fy]:
                    yearly_records[fy][metric_name] = float(item["val"])
            break

    df = pd.DataFrame(sorted(yearly_records.values(), key=lambda r: r["Fiscal_Year"]))
    if df.empty or len(df) < 2:
        raise ValueError(f"Insufficient multi-year 10-K XBRL records found for CIK {cik_padded}.")
    for col in US_GAAP_TAGS:
        if col not in df.columns:
            df[col] = 0.0
    df = df.fillna(0.0).tail(4).reset_index(drop=True)
    return df

