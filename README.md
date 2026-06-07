---
title: DEEN BI
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: app.py
pinned: false
---
# 📊 DEEN Business Intelligence
### **AI-Powered Predictive Operations Intelligence System**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://deen-ops.streamlit.app/)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-Senior%2B-blueviolet)](https://github.com/saajiidi/DEEN-AI-Dashboard)
[![CI](https://github.com/Sajid-ul-Islam/DEEN-BI/actions/workflows/ci.yml/badge.svg)](https://github.com/Sajid-ul-Islam/DEEN-BI/actions/workflows/ci.yml)
[![Streamlit Demo](https://img.shields.io/badge/Streamlit-Demo-FF4B4B?logo=streamlit)](https://deen-ops.streamlit.app/)

**Live Demo:** [https://deen-ops.streamlit.app/](https://deen-ops.streamlit.app/)

"Most dashboards visualize. This terminal explains, predicts, and recommends."

> 🤖 **AI Agents**: See [`agents.md`](agents.md) for comprehensive codebase blueprint, architecture patterns, and extension guidelines.

---

## 🎬 Quick Demo

![DEEN BI Dashboard](https://raw.githubusercontent.com/Sajid-ul-Islam/DEEN-BI/main/assets/Business-Analysis-cover.png)
*Figure: Sales Analytics Overview with ML Forecasting*

---

## 🔴 The Problem
Standard BI tools provide charts but lack **contextual intelligence**. Management is often left asking: *"Why did sales drop?"*, *"Which products should we bundle?"*, or *"When will we run out of stock for our top kits?"*

## ✅ The Solution: DEEN OPS Terminal
A professional-grade **Operational Command Center** designed for high-velocity E-commerce. It transforms raw WooCommerce data into an actionable decision-support system using multi-tier machine learning.

---

## 🧠 Core Intelligence Pillars

### 1. Enterprise-Grade AutoML Forecasting
Unlike simple linear trends, our **Smart Model Router** automatically evaluates the dataset's characteristics (stationarity, seasonality, sparsity) to select the optimal model from our tournament. For a technical breakdown of the algorithms used, see the [Forecasting Model Zoo in skill.md](skill.md#6-forecasting-model-zoo-automl-engine).
*   **Tier 1 (Statistical):** Exponential Smoothing (Holt-Winters), Ridge/LASSO Regression.
*   **Tier 2 (Classical):** SARIMA, **Croston's Method** (for intermittent/sparse demand).
*   **Tier 3 (Supervised ML):** XGBoost, LightGBM with rolling feature engineering.
*   **Tier 4 (Deep Learning):** Prophet and LSTM for complex long-term dependencies.
*   **Caching:** Heavily optimized with `@st.cache_data` and `@st.cache_resource` for aggressive performance.

### 2. Market Basket & Affinity Analysis (MBA)
Discover hidden revenue opportunities using association rule learning (Apriori).
*   **Support/Confidence/Lift Metrics:** Identify which products are "better together".
*   **Attachment Rate tracking:** Monitor the performance of strategic product pairings.

### 3. Bundle-Aware Inventory Intelligence
The system joins real-time stock levels with sales affinity data to prevent "Orphan Stock":
*   **Bundle Fulfillment Rate:** Identifies the "bottleneck component" in popular kits.
*   **Orphan Stock Rate:** Detects capital trapped in accessories whose core product is OOS.
*   **Strategic Reorder Alerts:** Recommends joint purchases based on component dependency.

### 4. High-Fidelity Data Pipeline
*   **Auto-Fetch Engine:** Seamless background synchronization with external APIs.
*   **Dynamic Column Mapping:** Flexible ingestion logic that handles schema drift automatically.
*   **Anomaly Toasting:** Real-time UI notifications for unusual refund spikes or stockouts.

---

## 🛠️ Technology Stack
*   **Frontend:** Streamlit (Custom Material-Design CSS Override), Plotly.
*   **Backend:** Service-Oriented Architecture (SOA), Python 3.x.
*   **Machine Learning:** Scikit-Learn, Statsmodels, XGBoost, Prophet.
*   **Data Ops:** Pandas (Vectorized Ops), NumPy, Aiohttp (Async Syncing).

---

## 📸 System Walkthrough

![DEEN BI Dashboard](https://raw.githubusercontent.com/Sajid-ul-Islam/DEEN-BI/main/assets/Business-Analysis-cover.png)
*Figure: Real-time Operations Dashboard with AI Predictions*

---

## 🚀 Getting Started

1. **Clone & Install:**
   ```bash
   git clone https://github.com/Sajid-ul-Islam/DEEN-BI.git
   pip install -r requirements.txt
   ```
2. **Configure Secrets:**
   Create `.streamlit/secrets.toml` with your credentials:
   ```toml
   [woocommerce]
   store_url = "https://yourstore.com"
   consumer_key = "ck_your_consumer_key"
   consumer_secret = "cs_your_consumer_secret"
   ```
3. **Run Terminal:**
   ```bash
   streamlit run app.py
   ```

### 🔐 WooCommerce API Setup

To enable the **Customer Insight** module:

1. **Generate API Keys in WooCommerce:**
   - Go to **WooCommerce → Settings → Advanced → REST API**
   - Click **Add Key**
   - Set permissions to **"Read"** (minimum) or **"Read/Write"**
   - Copy the **Consumer Key** and **Consumer Secret**

2. **Configure Store Permalinks:**
   - Go to **Settings → Permalinks**
   - Select any option except "Plain" (required for REST API)
   - Save changes

3. **Add Credentials:**
   - Create `.streamlit/secrets.toml` in project root
   - Add the credentials as shown above

4. **Test Connection:**
   - Navigate to **👥 Customer Insight** in the sidebar
   - The module will verify connectivity automatically

---

## 🔄 Continuous Integration

DEEN-BI uses GitHub Actions for automated testing, linting, and type checking on every push and pull request to maintain code quality.

### CI Workflow

The CI pipeline runs the following checks on Ubuntu:

1. **Python Setup**: Python 3.10 environment
2. **Dependency Installation**:
   ```bash
   pip install -r requirements.txt
   pip install pytest ruff black mypy
   ```
3. **Type Checking**: MyPy static type analysis
4. **Syntax Validation**: Python `compileall` for syntax/indentation errors
5. **Linting**: Ruff with strict rules (E9, F63, F7, F82)
6. **Formatting**: Black code formatter check
7. **Tests**: Pytest with verbose output (`-v --tb=short`)

### Running CI Checks Locally

Developers can run the same checks locally:

```bash
# Install dev dependencies
pip install pytest ruff black mypy

# Type checking
mypy --ignore-missing-imports .

# Syntax check
python -m compileall -q .

# Linting
ruff check . --select=E9,F63,F7,F82
ruff check . --exit-zero

# Format check
black --check .

# Tests
pytest tests/ -v --tb=short
```

### CI Status Badge

[![CI](https://github.com/Sajid-ul-Islam/DEEN-BI/actions/workflows/ci.yml/badge.svg)](https://github.com/Sajid-ul-Islam/DEEN-BI/actions/workflows/ci.yml)

---
**Engineered with precision for DEEN Commerce.**
*Primary Developer: Sajid Islam*
