# DEEN BI Development Guide

This document provides development guidelines and notes for extending the DEEN Business Intelligence system.

---

## Extending Customer Insight Filters

The Customer Insight module provides a flexible filter system. Here's how to extend it:

### Architecture Overview

```
src/components/customer_insight/
├── customer_filters.py      # Filter UI and logic
├── customer_selector.py       # Customer list display
├── customer_report.py         # Detailed reports
└── order_history_table.py     # Order display
```

### Adding a New Filter

#### 1. Add UI Control in `customer_filters.py`

Add a new expander section in `render_customer_filters()`:

```python
with st.expander("🆕 New Filter", expanded=False):
    st.caption("Description of the new filter")
    
    new_value = st.number_input(
        "Filter Label",
        min_value=0,
        max_value=1000,
        value=st.session_state.get(f"{key_prefix}_new_filter", 0),
        key=f"{key_prefix}_new_filter_input",
    )
    st.session_state[f"{key_prefix}_new_filter"] = new_value
```

#### 2. Update Filter Dictionary

Add the new filter to the return dictionary:

```python
filters = {
    # ... existing filters
    "new_filter": st.session_state.get(f"{key_prefix}_new_filter", 0),
}
```

#### 3. Implement Filter Logic in `apply_customer_filters()`

```python
def apply_customer_filters(orders_df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    # ... existing filters
    
    # New filter implementation
    if filters.get("new_filter", 0) > 0:
        customers_df = customers_df[customers_df["some_column"] >= filters["new_filter"]]
    
    return customers_df
```

#### 4. Add Helper Function (if needed)

In `src/utils/woocommerce_helpers.py`:

```python
def calculate_new_metric(data: pd.DataFrame) -> float:
    """Calculate new metric for filtering."""
    return data["column"].sum()  # Your calculation
```

### Filter Types Supported

#### Number Range Filter
```python
col1, col2 = st.columns(2)
with col1:
    min_val = st.number_input("Minimum", min_value=0, value=0)
with col2:
    max_val = st.number_input("Maximum", min_value=0, value=1000)
```

#### Date Range Filter
```python
start_date = st.date_input("Start date", value=date.today() - timedelta(days=30))
end_date = st.date_input("End date", value=date.today())
```

#### Multi-Select Filter
```python
options = {"Option 1": 1, "Option 2": 2}
selected = st.multiselect("Select options", options=list(options.keys()))
selected_ids = [options[s] for s in selected]
```

#### Boolean/Toggle Filter
```python
enabled = st.toggle("Enable filter", value=False)
```

### Filter Logic Patterns

#### AND Logic (Default)
All filters must match:
```python
if filter_a:
    df = df[df["col_a"] == filter_a]
if filter_b:
    df = df[df["col_b"] == filter_b]
# Both conditions applied
```

#### OR Logic
Any filter can match:
```python
mask = pd.Series(False, index=df.index)
if filter_a:
    mask |= df["col_a"] == filter_a
if filter_b:
    mask |= df["col_b"] == filter_b
df = df[mask]
```

### Testing New Filters

1. **Unit Test**: Create test in `tests/test_customer_filters.py`
```python
def test_new_filter():
    filters = {"new_filter": 100}
    result = apply_customer_filters(sample_data, filters)
    assert len(result) == expected_count
```

2. **Manual Test**: Run app and verify:
   - Filter UI displays correctly
   - Filter applies correctly
   - Reset button clears filter
   - Cache refresh works with filter

3. **Edge Cases**: Test with:
   - Empty data
   - Maximum values
   - Invalid inputs
   - Combined with other filters

### Performance Considerations

- Filters are applied in sequence (early filters reduce data for later ones)
- Date filtering should happen first (most restrictive)
- Aggregated filters (amount, orders) happen after aggregation
- Use `st.cache_data` for expensive operations
- Consider adding progress indicators for slow filters

### Best Practices

1. **Naming**: Use descriptive filter names in UI
2. **Defaults**: Set sensible defaults that don't restrict data
3. **Validation**: Validate min/max relationships (min < max)
4. **Help Text**: Add `help=` parameter to explain filter purpose
5. **Session State**: Persist filter values in session state
6. **Reset**: Ensure reset button clears the new filter
7. **Documentation**: Update this guide with new filter details

---

## API Client Development

### Extending BaseAPIClient

When creating a new API client:

```python
from src.inheritance.base_api_client import BaseAPIClient, APIConfig

class NewAPIClient(BaseAPIClient):
    def __init__(self, api_key: str, base_url: str):
        config = APIConfig(
            base_url=base_url,
            timeout=60,
            max_retries=3,
        )
        super().__init__(config)
        self.api_key = api_key
    
    def _get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
    
    def _get_sensitive_keys(self) -> list[str]:
        return ["api_key", "password", "token"]
```

### Adding Retry Logic

Use the `retry_with_backoff` decorator:

```python
from src.inheritance.base_api_client import retry_with_backoff

@retry_with_backoff(max_retries=3, backoff_factor=1.0)
def fetch_critical_data(self):
    return self.get("critical/endpoint")
```

---

## Common Patterns

### Session State Management

```python
# Initialize with default
if "my_key" not in st.session_state:
    st.session_state.my_key = default_value

# Update
st.session_state.my_key = new_value

# Clear
if st.button("Reset"):
    del st.session_state.my_key
```

### Data Caching

```python
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_expensive_data(param: str) -> pd.DataFrame:
    # Expensive operation
    return result
```

### Error Handling

```python
try:
    data = fetch_data()
except APIError as e:
    st.error(f"API Error: {e.message}")
    if e.status_code == 401:
        st.info("Check your API credentials")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    st.error("An unexpected error occurred")
```

---

## Testing Guidelines

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_customer_insight/

# With coverage
pytest --cov=src tests/
```

### Test Data

Create fixtures in `tests/conftest.py`:

```python
import pytest
import pandas as pd

@pytest.fixture
def sample_orders():
    return pd.DataFrame({
        "order_id": [1, 2, 3],
        "total": [100, 200, 300],
        "customer_id": [1, 1, 2],
    })
```

---

## Deployment Notes

### Pre-deployment Checklist

- [ ] All tests pass
- [ ] Requirements.txt updated
- [ ] Documentation updated
- [ ] Secrets template created
- [ ] No hardcoded credentials
- [ ] Error messages are user-friendly
- [ ] Caching TTL is appropriate

### Environment Variables

Create `.env` template:

```bash
# .env.template
WOOCOMMERCE_STORE_URL=https://example.com
WOOCOMMERCE_CONSUMER_KEY=ck_...
WOOCOMMERCE_CONSUMER_SECRET=cs_...
```

---

*Last updated: 2024*
