# AI Business Insights Dashboard

A Streamlit dashboard that lets non-technical managers ask plain-English
questions about company sales data and get AI-generated answers,
executive summaries, and recommendations — grounded in real SQL
aggregates, not hallucinated numbers.

## Features

- **Data cleaning** (`clean_data.py`) — handles missing values, duplicates,
  type fixes, derived columns (margin, year-month).
- **KPI dashboard** — revenue/profit trend, revenue by product, revenue by
  region, all computed via SQL queries against a local SQLite database.
- **AI executive summary** — Gemini-generated 4-6 sentence summary of
  performance, grounded in the same SQL aggregates shown on the dashboard.
- **Natural language Q&A** — chat interface; ask things like "Why did
  sales drop last month?" or "Which products are losing revenue?"
- **Automated recommendations** — numbered, data-justified suggestions
  for next quarter.

## Architecture

```
generate_data.py   -> data/raw_sales.csv      (synthetic data, intentional dip + product trends)
clean_data.py       -> data/clean_sales.csv    (cleaned data)
db.py                -> data/sales.db           (SQLite; KPI queries live here)
ai_helpers.py        -> Gemini API calls, fed by db.py aggregates as context
app.py                -> Streamlit UI (3 pages: KPIs, Q&A, Summary/Recs)
```

**Why pre-aggregated context instead of text-to-SQL?** The AI Q&A feature
builds a compact text summary of the company's key aggregates (KPIs,
monthly trend, per-product trend, regional split) and passes that as
context to every prompt, rather than letting the LLM write its own SQL
against the database. This avoids SQL-injection-style risks from
LLM-generated queries and keeps every answer traceable to a real number
you can also see on the dashboard. (A natural "v2" extension is to add
text-to-SQL with a read-only DB user and a query validator — see
"Possible Extensions" below.)

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Gemini API key
cp .env.example .env
# then edit .env and paste your key in place of the placeholder
# get a free key at https://aistudio.google.com/apikey

# 4. Build the data pipeline (run once, in order)
python3 generate_data.py   # creates data/raw_sales.csv
python3 clean_data.py      # creates data/clean_sales.csv
python3 db.py              # creates data/sales.db

# 5. Launch the dashboard
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Using your own data instead of synthetic data

Replace `data/raw_sales.csv` with your own file, keeping these columns
(rename/adapt `clean_data.py` if your column names differ):

```
order_id, order_date, product, category, region, quantity, unit_price, discount, revenue, cost, profit
```

Then run `clean_data.py` and `db.py` again before launching the app.

## Possible Extensions

- **Text-to-SQL Q&A**: let the LLM generate SQL queries directly against
  a read-only database connection, with a validator that rejects
  anything other than `SELECT` statements, for more flexible questions.
- **Power BI companion report**: point Power BI at `data/sales.db` or
  `data/clean_sales.csv` for stakeholders who prefer that tool.
- **Anomaly detection**: flag months/products with statistically unusual
  swings automatically, rather than relying on the LLM to notice them.
- **Multi-tenant / file upload**: let users upload their own CSV from
  the Streamlit UI instead of editing files on disk.
- **Caching AI responses**: cache summaries/recommendations per dataset
  hash to avoid repeated API calls and cost.

## Tech Stack

Python, Pandas, SQL (SQLite), Streamlit, Plotly, Google Gemini API.

## Skills Demonstrated

Data Analysis, SQL, Data Visualization, Prompt Engineering, LLM
Integration, Data Pipeline Design.

## Live demo
[business-dash.streamlit.app](https://business-dash.streamlit.app)

## 👤 Author

**Vikash Verma**
Aspiring Data Analyst | Excel · SQL · Power BI · Python | E-mail- vikashverma566@gmail.com

---
