"""
Institutional Financial Forensic & Bankruptcy Scoring Engine
Computes Altman Z-Score, Piotroski F-Score (0-9), and Beneish M-Score from audited financials.
"""

import pandas as pd


def compute_forensic_scores(df: pd.DataFrame, market_cap_usd: float) -> dict:
    """Computes Altman Z-Score, Piotroski F-Score, and Beneish M-Score for the latest fiscal year."""
    if len(df) < 2:
        raise ValueError("At least 2 consecutive fiscal years are required for YoY forensic ratios.")

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    ta = max(float(curr["TotalAssets"]), 1.0)
    ta_prev = max(float(prev["TotalAssets"]), 1.0)
    rev = max(float(curr["Revenue"]), 1.0)
    rev_prev = max(float(prev["Revenue"]), 1.0)

    # 1. Altman Z-Score (Manufacturing / General Corporate Standard)
    wc = float(curr["CurrentAssets"]) - float(curr["CurrentLiabilities"])
    tl = max(float(curr["TotalLiabilities"]), 1.0)
    mve = max(float(market_cap_usd), float(curr["StockholdersEquity"]), 1.0)

    x1 = wc / ta
    x2 = float(curr["RetainedEarnings"]) / ta
    x3 = float(curr["OperatingIncome"]) / ta
    x4 = mve / tl
    x5 = rev / ta
    altman_z = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5, 2)
    z_zone = "SAFE ZONE (> 2.99)" if altman_z > 2.99 else ("GREY ZONE (1.81–2.99)" if altman_z >= 1.81 else "DISTRESS RISK (< 1.81)")

    # 2. Piotroski F-Score (0 to 9 Binary Fundamental Strength Criteria)
    roa = float(curr["NetIncome"]) / ta
    roa_prev = float(prev["NetIncome"]) / ta_prev
    cfo = float(curr["OperatingCashFlow"])
    ltd_ratio = float(curr["LongTermDebt"]) / ta
    ltd_ratio_prev = float(prev["LongTermDebt"]) / ta_prev
    cr = float(curr["CurrentAssets"]) / max(float(curr["CurrentLiabilities"]), 1.0)
    cr_prev = float(prev["CurrentAssets"]) / max(float(prev["CurrentLiabilities"]), 1.0)
    gm = float(curr["GrossProfit"]) / rev
    gm_prev = float(prev["GrossProfit"]) / rev_prev
    at = rev / ta
    at_prev = rev_prev / ta_prev

    f_signals = {
        "F1_Positive_Net_Income": int(float(curr["NetIncome"]) > 0),
        "F2_Positive_Operating_Cash_Flow": int(cfo > 0),
        "F3_Improving_ROA_YoY": int(roa > roa_prev),
        "F4_Quality_of_Earnings_CFO_gt_NI": int(cfo > float(curr["NetIncome"])),
        "F5_Lower_LongTerm_Leverage": int(ltd_ratio <= ltd_ratio_prev),
        "F6_Higher_Current_Ratio": int(cr > cr_prev),
        "F7_No_Equity_Dilution_Proxy": int(float(curr["StockholdersEquity"]) >= float(prev["StockholdersEquity"]) * 0.95),
        "F8_Expanding_Gross_Margin": int(gm > gm_prev),
        "F9_Higher_Asset_Turnover": int(at > at_prev),
    }
    f_score = sum(f_signals.values())
    f_grade = "STRONG FUNDAMENTALS (7–9)" if f_score >= 7 else ("MODERATE (4–6)" if f_score >= 4 else "WEAK FUNDAMENTALS (0–3)")

    # 3. Beneish M-Score (8-Variable Earnings Manipulation Model; > -1.78 flags risk)
    dsri = ((float(curr["AccountsReceivable"]) / rev) / max(float(prev["AccountsReceivable"]) / rev_prev, 1e-6)) if float(prev["AccountsReceivable"]) > 0 else 1.0
    gmi = (gm_prev / max(gm, 1e-6)) if gm > 0 else 1.0
    hard_curr = float(curr["CurrentAssets"]) + float(curr["PPE_Net"])
    hard_prev = float(prev["CurrentAssets"]) + float(prev["PPE_Net"])
    aqi = ((1.0 - hard_curr / ta) / max(1.0 - hard_prev / ta_prev, 1e-6)) if (1.0 - hard_prev / ta_prev) > 0.01 else 1.0
    sgi = rev / rev_prev
    dep_rate_curr = float(curr["Depreciation"]) / max(float(curr["Depreciation"]) + float(curr["PPE_Net"]), 1.0)
    dep_rate_prev = float(prev["Depreciation"]) / max(float(prev["Depreciation"]) + float(prev["PPE_Net"]), 1.0)
    depi = (dep_rate_prev / max(dep_rate_curr, 1e-6)) if dep_rate_curr > 0 else 1.0
    sgai = ((float(curr["SGA_Expense"]) / rev) / max(float(prev["SGA_Expense"]) / rev_prev, 1e-6)) if float(prev["SGA_Expense"]) > 0 else 1.0
    lvgi = ((float(curr["CurrentLiabilities"]) + float(curr["LongTermDebt"])) / ta) / max((float(prev["CurrentLiabilities"]) + float(prev["LongTermDebt"])) / ta_prev, 1e-6)
    tata = (float(curr["NetIncome"]) - cfo) / ta

    beneish_m = round(-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi, 2)
    m_flag = "MANIPULATION WARNING (> -1.78)" if beneish_m > -1.78 else "CLEAN EARNINGS QUALITY (<= -1.78)"

    return {
        "fiscal_year": int(curr["Fiscal_Year"]),
        "altman_z": altman_z,
        "z_zone": z_zone,
        "piotroski_f": f_score,
        "f_grade": f_grade,
        "f_signals": f_signals,
        "beneish_m": beneish_m,
        "m_flag": m_flag,
        "roa_pct": round(roa * 100.0, 2),
        "gross_margin_pct": round(gm * 100.0, 2),
        "current_ratio": round(cr, 2),
        "accruals_to_assets_pct": round(tata * 100.0, 2),
    }
