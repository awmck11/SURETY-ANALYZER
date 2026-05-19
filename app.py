import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Surety Underwriting Analyzer",
    page_icon="🏗️",
    layout="wide",
)

st.title("Surety Underwriting Analyzer")
st.caption("Contractor financial health analysis using Schleifer-aligned underwriting framework")


# =====================================================
# CALCULATIONS (with defensive None checks)
# =====================================================

def calc_wc(ca, cl):
    if ca is None or cl is None: return None
    return ca - cl

def calc_cr(ca, cl):
    if ca is None or cl is None or cl == 0: return None
    return ca / cl

def calc_qr(ca, inv, pp, cl):
    if ca is None or cl is None or cl == 0: return None
    return (ca - (inv or 0) - (pp or 0)) / cl

def calc_de(td, te):
    if td is None or te is None or te == 0: return None
    return td / te

def calc_er(te, ta):
    if te is None or ta is None or ta == 0: return None
    return te / ta

def calc_gpm(gp, rev):
    if gp is None or rev is None or rev == 0: return None
    return gp / rev

def calc_npm(ni, rev):
    if ni is None or rev is None or rev == 0: return None
    return ni / rev

def calc_roe(ni, te):
    if ni is None or te is None or te == 0: return None
    return ni / te

def calc_wc_rev(wc, rev):
    if wc is None or rev is None or rev == 0: return None
    return wc / rev


# =====================================================
# FLAGGING (with adjustable thresholds)
# =====================================================

def flag_current_ratio(r, t):
    if r is None: return "N/A"
    if r < t["cr_red"]: return "RED FLAG"
    elif r < t["cr_tight"]: return "TIGHT"
    elif r < t["cr_acceptable"]: return "ACCEPTABLE"
    elif r < t["cr_strong"]: return "STRONG"
    else: return "VERY STRONG"

def flag_quick_ratio(r, t):
    if r is None: return "N/A"
    if r < t["qr_red"]: return "RED FLAG"
    elif r < t["qr_tight"]: return "TIGHT"
    elif r < t["qr_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"

def flag_de(r, t):
    if r is None: return "N/A"
    if r > t["de_red"]: return "RED FLAG"
    elif r > t["de_high"]: return "HIGH RISK"
    elif r > t["de_moderate"]: return "MODERATE"
    elif r > t["de_conservative"]: return "CONSERVATIVE"
    else: return "VERY CONSERVATIVE"

def flag_er(r, t):
    if r is None: return "N/A"
    if r < t["er_red"]: return "RED FLAG"
    elif r < t["er_tight"]: return "TIGHT"
    elif r < t["er_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"

def flag_gpm_v(m, t):
    if m is None: return "N/A"
    if m < t["gpm_red"]: return "RED FLAG"
    elif m < t["gpm_tight"]: return "TIGHT"
    elif m < t["gpm_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"

def flag_npm_v(m, t):
    if m is None: return "N/A"
    if m < 0: return "RED FLAG"
    elif m < t["npm_tight"]: return "TIGHT"
    elif m < t["npm_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"

def flag_roe_v(r, t):
    if r is None: return "N/A"
    if r < 0: return "RED FLAG"
    elif r < t["roe_weak"]: return "WEAK"
    elif r < t["roe_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"

def flag_wc_rev_v(r, t):
    if r is None: return "N/A"
    if r < t["wcrev_red"]: return "RED FLAG"
    elif r < t["wcrev_tight"]: return "TIGHT"
    elif r < t["wcrev_acceptable"]: return "ACCEPTABLE"
    else: return "STRONG"


def flag_trend(values, higher_is_better=True, volatility_threshold=0.75):
    clean = [v for v in values if v is not None and not pd.isna(v)]
    if len(clean) < 2:
        return "INSUFFICIENT DATA"
    first, last = clean[0], clean[-1]
    change = (last - first) / abs(first) if first != 0 else 0
    avg = sum(clean) / len(clean)
    spread = (max(clean) - min(clean)) / abs(avg) if avg != 0 else 0
    if spread > volatility_threshold:
        return "VOLATILE"
    threshold = 0.10
    if higher_is_better:
        if change > threshold: return "IMPROVING"
        elif change < -threshold: return "DETERIORATING"
        else: return "STABLE"
    else:
        if change > threshold: return "DETERIORATING"
        elif change < -threshold: return "IMPROVING"
        else: return "STABLE"


def calc_growth_rate(values):
    clean = [v for v in values if v is not None and not pd.isna(v)]
    if len(clean) < 2: return None
    growth_rates = []
    for i in range(1, len(clean)):
        if clean[i-1] != 0:
            growth_rates.append((clean[i] - clean[i-1]) / abs(clean[i-1]))
    return sum(growth_rates) / len(growth_rates) if growth_rates else None


def flag_growth(g):
    if g is None: return "INSUFFICIENT DATA"
    if g > 0.40: return "RED FLAG - rapid growth"
    elif g > 0.20: return "ELEVATED"
    elif g > 0.05: return "HEALTHY GROWTH"
    elif g > -0.05: return "FLAT"
    else: return "DECLINING"


# =====================================================
# DATA FETCHING
# =====================================================

def safe_get(df, row_name, column):
    try:
        value = df.loc[row_name, column]
        if pd.isna(value): return None
        return float(value)
    except (KeyError, IndexError):
        return None


def fetch_yfinance(ticker):
    company = yf.Ticker(ticker)
    info = company.info
    name = info.get("longName", ticker)
    bs = company.balance_sheet
    is_ = company.income_stmt
    if bs.empty or is_.empty:
        return None
    bs_cols = list(bs.columns)[::-1]
    is_cols = list(is_.columns)[::-1]
    years = []
    for bc, ic in zip(bs_cols, is_cols):
        years.append({
            "year": bc.year,
            "current_assets": safe_get(bs, "Current Assets", bc),
            "current_liabilities": safe_get(bs, "Current Liabilities", bc),
            "inventory": safe_get(bs, "Inventory", bc) or 0,
            "prepaids": safe_get(bs, "Other Current Assets", bc) or 0,
            "total_assets": safe_get(bs, "Total Assets", bc),
            "total_equity": safe_get(bs, "Stockholders Equity", bc),
            "total_debt": safe_get(bs, "Total Debt", bc),
            "revenue": safe_get(is_, "Total Revenue", ic),
            "gross_profit": safe_get(is_, "Gross Profit", ic),
            "net_income": safe_get(is_, "Net Income", ic),
        })
    return {"name": name, "ticker": ticker, "years": years}


def parse_uploaded_csv(file, contractor_name):
    """Expects CSV with columns: year, current_assets, current_liabilities, inventory, prepaids, total_assets, total_equity, total_debt, revenue, gross_profit, net_income"""
    df = pd.read_csv(file)
    years = []
    for _, row in df.iterrows():
        years.append({
            "year": int(row["year"]),
            "current_assets": float(row["current_assets"]),
            "current_liabilities": float(row["current_liabilities"]),
            "inventory": float(row.get("inventory", 0) or 0),
            "prepaids": float(row.get("prepaids", 0) or 0),
            "total_assets": float(row["total_assets"]),
            "total_equity": float(row["total_equity"]),
            "total_debt": float(row["total_debt"]),
            "revenue": float(row["revenue"]),
            "gross_profit": float(row["gross_profit"]),
            "net_income": float(row["net_income"]),
        })
    return {"name": contractor_name, "ticker": "PRIVATE", "years": years}


# =====================================================
# ANALYSIS
# =====================================================

def analyze(contractor, t):
    name = contractor["name"]
    ticker = contractor["ticker"]
    years = contractor["years"]

    rows = []
    revs, eqs, gpms, npms, des = [], [], [], [], []

    for y in years:
        if not y["current_assets"] or not y["current_liabilities"]:
            continue
        wc = calc_wc(y["current_assets"], y["current_liabilities"])
        cr = calc_cr(y["current_assets"], y["current_liabilities"])
        qr = calc_qr(y["current_assets"], y["inventory"], y["prepaids"], y["current_liabilities"])
        de = calc_de(y["total_debt"], y["total_equity"])
        er = calc_er(y["total_equity"], y["total_assets"])
        gpm = calc_gpm(y["gross_profit"], y["revenue"])
        npm = calc_npm(y["net_income"], y["revenue"])
        roe = calc_roe(y["net_income"], y["total_equity"])
        wc_rev = calc_wc_rev(wc, y["revenue"])

        rows.append({
            "Year": y["year"],
            "Revenue ($M)": y["revenue"] / 1e6 if y["revenue"] else None,
            "Equity ($M)": y["total_equity"] / 1e6 if y["total_equity"] else None,
            "Working Capital ($M)": wc / 1e6 if wc is not None else None,
            "Current Ratio": cr,
            "Quick Ratio": qr,
            "Debt-to-Equity": de,
            "Equity Ratio": er,
            "Gross Profit Margin": gpm,
            "Net Profit Margin": npm,
            "Return on Equity": roe,
            "WC to Revenue": wc_rev,
        })

        if y["revenue"]: revs.append(y["revenue"])
        if y["total_equity"]: eqs.append(y["total_equity"])
        if gpm is not None: gpms.append(gpm)
        if npm is not None: npms.append(npm)
        if de is not None: des.append(de)

    trends = {
        "Revenue Growth": calc_growth_rate(revs),
        "Revenue Growth Flag": flag_growth(calc_growth_rate(revs)),
        "Equity Growth": calc_growth_rate(eqs),
        "Equity Growth Flag": flag_growth(calc_growth_rate(eqs)),
        "Gross Margin Trend": flag_trend(gpms, True, t["volatility"]),
        "Net Margin Trend": flag_trend(npms, True, t["volatility"]),
        "D/E Trend": flag_trend(des, False, t["volatility"]),
    }

    snapshot = {}
    latest = rows[-1] if rows else None
    if latest:
        snapshot = {
            "Current Ratio": flag_current_ratio(latest["Current Ratio"], t),
            "Quick Ratio": flag_quick_ratio(latest["Quick Ratio"], t),
            "Debt-to-Equity": flag_de(latest["Debt-to-Equity"], t),
            "Equity Ratio": flag_er(latest["Equity Ratio"], t),
            "Gross Profit Margin": flag_gpm_v(latest["Gross Profit Margin"], t),
            "Net Profit Margin": flag_npm_v(latest["Net Profit Margin"], t),
            "Return on Equity": flag_roe_v(latest["Return on Equity"], t),
            "WC to Revenue": flag_wc_rev_v(latest["WC to Revenue"], t),
        }

    verdict, reasoning = compute_verdict(snapshot, trends)

    return {
        "name": name, "ticker": ticker, "rows": rows,
        "trends": trends, "snapshot": snapshot,
        "verdict": verdict, "reasoning": reasoning,
    }


def compute_verdict(snapshot, trends):
    red_count = sum(1 for f in snapshot.values() if "RED FLAG" in f)
    tight_count = sum(1 for f in snapshot.values() if f in ["TIGHT", "WEAK"])
    trend_warnings = 0
    for k in ["Gross Margin Trend", "Net Margin Trend", "D/E Trend"]:
        if trends.get(k) == "DETERIORATING":
            trend_warnings += 1
    if trends.get("Revenue Growth Flag") == "RED FLAG - rapid growth":
        trend_warnings += 1
    if trends.get("Equity Growth Flag") == "DECLINING":
        trend_warnings += 1

    if red_count >= 3 or trend_warnings >= 3:
        return "DECLINE", "Multiple red flags or deteriorating trends across pillars."
    elif red_count >= 2:
        return "DECLINE OR HEAVILY CONDITIONED", "Significant credit concerns; bondable only with collateral or capacity restrictions."
    elif red_count == 1 or tight_count >= 3 or trend_warnings >= 2:
        return "APPROVE WITH CONDITIONS", "Bondable with monitoring; specific items require explanation or follow-up."
    elif tight_count >= 1 or trend_warnings >= 1:
        return "APPROVE - STANDARD MONITORING", "Acceptable risk with routine quarterly review."
    else:
        return "APPROVE - PREFERRED", "Strong across all pillars; candidate for expanded capacity."


# =====================================================
# COLOR HELPERS
# =====================================================

def color_for_flag(flag):
    if not flag or flag == "N/A":
        return ""
    f = str(flag).upper()
    if "RED FLAG" in f or "HIGH RISK" in f or "DETERIORATING" in f or "DECLINING" in f or "DECLINE" in f:
        return "background-color: #F8CBAD; color: #000;"
    if "TIGHT" in f or "WEAK" in f or "MODERATE" in f or "ELEVATED" in f or "VOLATILE" in f or "CONDITIONS" in f:
        return "background-color: #FFE699; color: #000;"
    if "STRONG" in f or "IMPROVING" in f or "HEALTHY" in f or "ACCEPTABLE" in f or "CONSERVATIVE" in f or "PREFERRED" in f or "APPROVE" in f or "STABLE" in f:
        return "background-color: #C6E0B4; color: #000;"
    return ""


# =====================================================
# EXCEL EXPORT
# =====================================================

def build_excel(analyses):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_data = []
        for a in analyses:
            summary_data.append({
                "Company": a["name"],
                "Ticker": a["ticker"],
                "Verdict": a["verdict"],
                "Reasoning": a["reasoning"],
                "Revenue Growth": a["trends"]["Revenue Growth"],
                "Equity Growth": a["trends"]["Equity Growth"],
                "GPM Trend": a["trends"]["Gross Margin Trend"],
                "NPM Trend": a["trends"]["Net Margin Trend"],
                "D/E Trend": a["trends"]["D/E Trend"],
            })
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Executive Summary", index=False)
        for a in analyses:
            df = pd.DataFrame(a["rows"])
            df.to_excel(writer, sheet_name=a["ticker"][:30], index=False)
    output.seek(0)
    return output


# =====================================================
# SIDEBAR: THRESHOLDS
# =====================================================

def threshold_sidebar():
    st.sidebar.header("Underwriting Thresholds")
    st.sidebar.caption("Adjust thresholds to match your underwriting personality.")

    with st.sidebar.expander("Liquidity (Current Ratio)", expanded=False):
        cr_red = st.slider("CR: Red Flag below", 0.5, 1.5, 1.0, 0.05)
        cr_tight = st.slider("CR: Tight below", 1.0, 1.5, 1.2, 0.05)
        cr_acceptable = st.slider("CR: Acceptable below", 1.2, 2.0, 1.5, 0.05)
        cr_strong = st.slider("CR: Strong below", 1.5, 2.5, 2.0, 0.05)

    with st.sidebar.expander("Liquidity (Quick Ratio)", expanded=False):
        qr_red = st.slider("QR: Red Flag below", 0.3, 1.0, 0.8, 0.05)
        qr_tight = st.slider("QR: Tight below", 0.6, 1.2, 1.0, 0.05)
        qr_acceptable = st.slider("QR: Acceptable below", 1.0, 2.0, 1.5, 0.05)

    with st.sidebar.expander("Leverage (D/E)", expanded=False):
        de_conservative = st.slider("D/E: Conservative below", 0.1, 1.0, 0.5, 0.1)
        de_moderate = st.slider("D/E: Moderate below", 0.5, 1.5, 1.0, 0.1)
        de_high = st.slider("D/E: High Risk above", 1.0, 3.0, 2.0, 0.1)
        de_red = st.slider("D/E: Red Flag above", 2.0, 5.0, 3.0, 0.1)

    with st.sidebar.expander("Equity Ratio", expanded=False):
        er_red = st.slider("ER: Red Flag below", 0.05, 0.30, 0.15, 0.01)
        er_tight = st.slider("ER: Tight below", 0.15, 0.40, 0.25, 0.01)
        er_acceptable = st.slider("ER: Acceptable below", 0.30, 0.60, 0.40, 0.01)

    with st.sidebar.expander("Profitability", expanded=False):
        gpm_red = st.slider("GPM: Red Flag below", 0.0, 0.15, 0.05, 0.01)
        gpm_tight = st.slider("GPM: Tight below", 0.05, 0.20, 0.10, 0.01)
        gpm_acceptable = st.slider("GPM: Acceptable below", 0.10, 0.30, 0.20, 0.01)
        npm_tight = st.slider("NPM: Tight below", 0.0, 0.05, 0.02, 0.005)
        npm_acceptable = st.slider("NPM: Acceptable below", 0.02, 0.10, 0.05, 0.005)
        roe_weak = st.slider("ROE: Weak below", 0.0, 0.15, 0.05, 0.01)
        roe_acceptable = st.slider("ROE: Acceptable below", 0.05, 0.25, 0.15, 0.01)

    with st.sidebar.expander("Balance Sheet Support", expanded=False):
        wcrev_red = st.slider("WC/Rev: Red Flag below", 0.0, 0.10, 0.05, 0.005)
        wcrev_tight = st.slider("WC/Rev: Tight below", 0.05, 0.15, 0.08, 0.005)
        wcrev_acceptable = st.slider("WC/Rev: Acceptable below", 0.10, 0.25, 0.15, 0.01)

    with st.sidebar.expander("Trend Analysis", expanded=False):
        volatility = st.slider("Volatility threshold (spread/mean)", 0.25, 1.5, 0.75, 0.05)

    return {
        "cr_red": cr_red, "cr_tight": cr_tight, "cr_acceptable": cr_acceptable, "cr_strong": cr_strong,
        "qr_red": qr_red, "qr_tight": qr_tight, "qr_acceptable": qr_acceptable,
        "de_conservative": de_conservative, "de_moderate": de_moderate, "de_high": de_high, "de_red": de_red,
        "er_red": er_red, "er_tight": er_tight, "er_acceptable": er_acceptable,
        "gpm_red": gpm_red, "gpm_tight": gpm_tight, "gpm_acceptable": gpm_acceptable,
        "npm_tight": npm_tight, "npm_acceptable": npm_acceptable,
        "roe_weak": roe_weak, "roe_acceptable": roe_acceptable,
        "wcrev_red": wcrev_red, "wcrev_tight": wcrev_tight, "wcrev_acceptable": wcrev_acceptable,
        "volatility": volatility,
    }


# =====================================================
# DISPLAY ANALYSIS
# =====================================================

def display_analysis(a):
    st.header(f"{a['name']} ({a['ticker']})")

    verdict_color = color_for_flag(a["verdict"])
    st.markdown(
        f"<div style='{verdict_color} padding: 15px; border-radius: 5px; font-size: 20px; font-weight: bold;'>"
        f"VERDICT: {a['verdict']}</div>",
        unsafe_allow_html=True
    )
    st.write(a["reasoning"])

    st.subheader("Year-by-Year Ratios")
    df = pd.DataFrame(a["rows"])
    format_dict = {
        "Revenue ($M)": "{:,.0f}",
        "Equity ($M)": "{:,.0f}",
        "Working Capital ($M)": "{:,.0f}",
        "Current Ratio": "{:.2f}",
        "Quick Ratio": "{:.2f}",
        "Debt-to-Equity": "{:.2f}",
        "Equity Ratio": "{:.2%}",
        "Gross Profit Margin": "{:.2%}",
        "Net Profit Margin": "{:.2%}",
        "Return on Equity": "{:.2%}",
        "WC to Revenue": "{:.2%}",
    }
    st.dataframe(df.style.format(format_dict, na_rep="N/A"), use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Schleifer Trend Analysis")
        rev_growth = a["trends"]["Revenue Growth"]
        eq_growth = a["trends"]["Equity Growth"]
        trend_rows = [
            ("Revenue Growth (avg YoY)", f"{rev_growth:.2%}" if rev_growth else "N/A", a["trends"]["Revenue Growth Flag"]),
            ("Equity Growth (avg YoY)", f"{eq_growth:.2%}" if eq_growth else "N/A", a["trends"]["Equity Growth Flag"]),
            ("Gross Margin Trend", "", a["trends"]["Gross Margin Trend"]),
            ("Net Margin Trend", "", a["trends"]["Net Margin Trend"]),
            ("D/E Trend", "", a["trends"]["D/E Trend"]),
        ]
        for label, value, flag in trend_rows:
            color = color_for_flag(flag)
            st.markdown(
                f"<div style='display: flex; justify-content: space-between; padding: 6px; margin: 2px 0; border-radius: 3px; {color}'>"
                f"<span><b>{label}</b> {value}</span><span>{flag}</span></div>",
                unsafe_allow_html=True
            )

    with col2:
        st.subheader("Latest Year Snapshot")
        for metric, flag in a["snapshot"].items():
            color = color_for_flag(flag)
            st.markdown(
                f"<div style='display: flex; justify-content: space-between; padding: 6px; margin: 2px 0; border-radius: 3px; {color}'>"
                f"<span><b>{metric}</b></span><span>{flag}</span></div>",
                unsafe_allow_html=True
            )


# =====================================================
# MAIN APP
# =====================================================

def main():
    thresholds = threshold_sidebar()

    st.markdown("---")

    mode = st.radio(
        "Choose input mode:",
        ["Public Ticker (Yahoo Finance)", "Upload CSV (Private Contractor)", "Sample Data"],
        horizontal=True,
    )

    analyses = []

    if mode == "Public Ticker (Yahoo Finance)":
        col1, col2 = st.columns([3, 1])
        with col1:
            tickers_input = st.text_input(
                "Enter tickers (comma-separated)",
                value="GVA, TPC, STRL",
                help="Examples: GVA (Granite), TPC (Tutor Perini), STRL (Sterling), DY (Dycom), MTRX (Matrix), PRIM (Primoris), FLR (Fluor)"
            )
        with col2:
            st.write("")
            st.write("")
            run = st.button("Run Analysis", type="primary", use_container_width=True)

        if run:
            tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
            for ticker in tickers:
                with st.spinner(f"Fetching {ticker}..."):
                    try:
                        contractor = fetch_yfinance(ticker)
                        if contractor is None:
                            st.error(f"Could not fetch data for {ticker}. Check ticker symbol.")
                            continue
                        analysis = analyze(contractor, thresholds)
                        analyses.append(analysis)
                    except Exception as e:
                        st.error(f"Error analyzing {ticker}: {e}")
                        continue

    elif mode == "Upload CSV (Private Contractor)":
        st.markdown(
            """
            **CSV format required**: columns named `year, current_assets, current_liabilities, 
            inventory, prepaids, total_assets, total_equity, total_debt, revenue, gross_profit, net_income`. 
            One row per fiscal year, dollar values (not millions).
            """
        )

        sample_df = pd.DataFrame({
            "year": [2022, 2023, 2024, 2025],
            "current_assets": [4500000, 5200000, 5800000, 6100000],
            "current_liabilities": [3100000, 3600000, 4200000, 4800000],
            "inventory": [200000, 220000, 250000, 280000],
            "prepaids": [80000, 90000, 100000, 110000],
            "total_assets": [8500000, 9200000, 10100000, 11000000],
            "total_equity": [2800000, 3100000, 3400000, 3600000],
            "total_debt": [1800000, 2000000, 2300000, 2500000],
            "revenue": [12000000, 14500000, 16800000, 18200000],
            "gross_profit": [1320000, 1595000, 1848000, 2002000],
            "net_income": [420000, 580000, 672000, 728000],
        })
        st.download_button(
            "Download CSV Template",
            sample_df.to_csv(index=False).encode("utf-8"),
            "sample_contractor_template.csv",
            "text/csv",
        )

        contractor_name = st.text_input("Contractor name", value="Private Contractor Inc.")
        uploaded = st.file_uploader("Upload CSV", type=["csv"])

        if uploaded:
            try:
                contractor = parse_uploaded_csv(uploaded, contractor_name)
                analysis = analyze(contractor, thresholds)
                analyses.append(analysis)
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    else:
        st.info("Running on built-in sample data: Granite, Tutor Perini, Sterling.")
        if st.button("Run Sample Analysis", type="primary"):
            for ticker in ["GVA", "TPC", "STRL"]:
                with st.spinner(f"Fetching {ticker}..."):
                    try:
                        contractor = fetch_yfinance(ticker)
                        if contractor is None:
                            continue
                        analysis = analyze(contractor, thresholds)
                        analyses.append(analysis)
                    except Exception as e:
                        st.error(f"Error analyzing {ticker}: {e}")
                        continue

    if analyses:
        st.markdown("---")
        st.subheader("Analysis Results")

        st.markdown("### Executive Summary")
        summary_rows = []
        for a in analyses:
            summary_rows.append({
                "Company": a["name"],
                "Ticker": a["ticker"],
                "Verdict": a["verdict"],
                "Revenue Growth": f"{a['trends']['Revenue Growth']:.2%}" if a['trends']['Revenue Growth'] else "N/A",
                "Equity Growth": f"{a['trends']['Equity Growth']:.2%}" if a['trends']['Equity Growth'] else "N/A",
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        for a in analyses:
            st.markdown("---")
            display_analysis(a)

        st.markdown("---")
        excel_file = build_excel(analyses)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            "Download Excel Report",
            data=excel_file,
            file_name=f"surety_analysis_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

main()