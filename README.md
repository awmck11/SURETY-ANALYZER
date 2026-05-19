# Surety Underwriting Analyzer

A Python-based contractor financial health analyzer built around the Schleifer red-flag framework used by surety underwriters. Pulls public company financials from Yahoo Finance (or accepts CSV uploads for private contractors), calculates surety-specific ratios across multiple years, applies Schleifer-aligned trend analysis, and produces an underwriting verdict with a downloadable Excel report.

Built as a pre-internship learning project before starting at Merchants Bonding Company (Summer 2026).

---

## What It Does

For any public construction contractor (by ticker) or any private contractor (via CSV upload), the tool:

1. Pulls or accepts up to 4 years of balance sheet and income statement data
2. Calculates 9 surety-relevant financial ratios per year (working capital, current ratio, quick ratio, debt-to-equity, equity ratio, gross profit margin, net profit margin, return on equity, working capital to revenue)
3. Applies adjustable underwriting thresholds to produce snapshot flags (RED FLAG / TIGHT / ACCEPTABLE / STRONG)
4. Analyzes the trend across years for each ratio (IMPROVING / STABLE / DETERIORATING / VOLATILE), explicitly flagging the Schleifer "profit fade" pattern
5. Calculates average year-over-year growth rates and flags rapid growth as a Schleifer Pillar 2 risk
6. Computes an overall underwriting verdict (APPROVE PREFERRED / STANDARD MONITORING / WITH CONDITIONS / HEAVILY CONDITIONED / DECLINE) using a moderate underwriting personality
7. Renders a color-coded report in the browser and exports a multi-tab formatted Excel file

---

## Why Schleifer

Tom Schleifer is the most influential voice in construction contractor failure analysis. His thesis: contractors don't fail from bad jobs, they fail from patterns of management behavior that show up in financials 12-18 months early. Five pillars:

1. **Volume vs. Balance Sheet** — overextension is the primary failure mode
2. **Growth is the most dangerous time** — most failures occur during expansion, not recession
3. **Profit fade** — declining margins predict failure better than any single year's number
4. **Cash flow discipline** — profitable contractors with bad cash management fail
5. **Profit drains** — death by 1,000 cuts

This tool addresses Pillars 1, 2, and 3 directly via ratio analysis and trend detection. Pillars 4 and 5 require project-level data not available in public filings.

---

## Tech Stack

- **Python 3.14** with pandas, yfinance, openpyxl, streamlit
- **VS Code** for development
- **Streamlit** for the web interface
- **Yahoo Finance** as the public data source

---

## How to Run

### Web App (recommended)

    python -m streamlit run app.py

Opens in your browser at http://localhost:8501. Choose input mode (public ticker, CSV upload, or sample data), adjust thresholds in the sidebar if desired, and run the analysis.

### Command Line Version

    python analyzer_v6.py

Runs on hardcoded tickers (GVA, TPC, STRL by default), produces a formatted Excel report in the project folder.

---

## Input Modes

**Public Ticker**: Enter any publicly-traded contractor's ticker. The tool pulls 4 years of 10-K data from Yahoo Finance automatically.

**CSV Upload**: For private contractors, upload a CSV with columns: year, current_assets, current_liabilities, inventory, prepaids, total_assets, total_equity, total_debt, revenue, gross_profit, net_income. A template is downloadable from within the app.

**Sample Data**: Runs analysis on Granite (GVA), Tutor Perini (TPC), and Sterling Infrastructure (STRL) for testing and demonstration.

---

## Adjustable Thresholds

Every flagging threshold is adjustable via sliders in the sidebar of the web app. This means the tool can be calibrated to:
- Conservative underwriting (heavy collateral requirements)
- Moderate underwriting (typical surety risk tolerance)
- Aggressive underwriting (rewards growth, faster approvals)

Default settings reflect moderate underwriting consistent with most mid-market surety appetite.

---

## Limitations

This tool is a starting point for underwriting analysis, not a replacement for it. Acknowledged limitations:

- **No backlog data** — not available on public financial statements, so Schleifer Pillar 1 (backlog-to-working-capital) cannot be fully evaluated for public companies
- **No project-level data** — cannot detect profit fade at the job level, only at the company level
- **Only handles public companies via API** — private contractor analysis requires CSV upload
- **Absolute thresholds, not peer benchmarks** — flags are based on industry-standard thresholds, not comparative analysis
- **Cannot capture qualitative factors** — management quality, customer concentration, geographic risk, and Schleifer Pillar 5 profit drains are all qualitative and outside the tool's scope

The tool surfaces what merits investigation. Underwriting judgment remains human.

---

## File Structure

    surety-analyzer/
    ├── app.py                # Streamlit web application (primary)
    ├── analyzer_v6.py        # Command-line version with Excel export
    ├── analyzer_v1.py        # Earlier development versions
    ├── analyzer_v2.py        # Earlier (multi-contractor)
    ├── analyzer_v3.py        # Earlier (yfinance integration)
    ├── analyzer_v4.py        # Earlier (Excel export)
    ├── analyzer_v5.py        # Earlier (multi-year + Schleifer trends)
    ├── README.md             # This file
    └── sample_data/          # Sample CSV files (optional)

---

## Built By

Alex McKane, Iowa State University Finance major, December 2026 graduation. Built May 2026 in preparation for Summer 2026 surety underwriting internship at Merchants Bonding Company. AI-assisted development (Claude); design choices, surety logic, threshold calibration, and architectural decisions are mine.