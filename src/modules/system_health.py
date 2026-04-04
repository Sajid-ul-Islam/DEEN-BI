import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from src.core.errors import get_logs, log_error
from src.core.paths import ERROR_LOG_FILE

def clear_error_logs():
    """Clears all logged errors."""
    if os.path.exists(ERROR_LOG_FILE):
        os.remove(ERROR_LOG_FILE)
        st.success("Error logs cleared.")
        st.rerun()

def render_system_health_tab():
    """Renders the System Health and Error Resolution hub."""
    st.header("⚡ System Health & Error Resolver")
    st.info("This module captures runtime exceptions and formats them for AI-assisted self-healing.")

    logs = get_logs()
    
    if not logs:
        st.success("🎉 No errors detected. System is running smoothly.")
        if st.button("Simulate Test Error"):
            try:
                1/0
            except Exception as e:
                log_error(e, context="Test Simulation", details={"trigger": "manual button"})
                st.toast("Test error logged.")
                st.rerun()
        return

    # Error Summary
    st.subheader(f"🚩 Reported Issues ({len(logs)})")
    
    # Convert to DataFrame for easier display
    df_errors = pd.DataFrame(logs)
    df_errors = df_errors.sort_values('timestamp', ascending=False)
    
    # Action Row
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🧹 Clear All Logs", use_container_width=True):
            clear_error_logs()
            
    # Display individual errors as Expanders
    for idx, entry in enumerate(logs[::-1]):
        with st.expander(f"🔴 {entry['timestamp']} | {entry['context']} | {entry['error'][:60]}..."):
            st.code(entry['error'], language="python")
            st.caption("Traceback:")
            st.code(entry['traceback'], language="python")
            
            # THE MAGIC BUTTON: Format for Prompt
            prompt_payload = f"""
### 🚨 SYSTEM ERROR DETECTED FOR FIXING

**Context:** {entry['context']}
**Error:** {entry['error']}
**Timestamp:** {entry['timestamp']}

---
**Traceback:**
```python
{entry['traceback']}
```
---
**Task:** Please analyze this error and provide a fix for the application.
"""
            st.markdown("---")
            st.subheader("🤖 AI Resolver Prompt")
            st.write("Copy the code block below and send it to your AI Developer (Antigravity):")
            st.code(prompt_payload, language="markdown")
            
            if st.button(f"Mark as Resolved #{idx}", key=f"res_{idx}"):
                # Simple way to 'resolve' is to remove from local list, 
                # but for now we just show a toast
                st.toast("Solution requested. Paste the prompt above to Antigravity.")

    # Detailed Table view
    st.divider()
    st.subheader("🔍 All System Logs")
    st.dataframe(df_errors[['timestamp', 'context', 'error']], use_container_width=True)
