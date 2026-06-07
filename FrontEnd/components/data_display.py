from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

def _safe_datetime_series(value) -> pd.Series:
    if value is None:
        return pd.Series(dtype="datetime64[ns]")
    converted = pd.to_datetime(value, errors="coerce")
    if isinstance(converted, pd.Series):
        return converted
    if isinstance(converted, pd.Index):
        return pd.Series(converted)
    if pd.isna(converted):
        return pd.Series(dtype="datetime64[ns]")
    return pd.Series([converted])






def file_summary(uploaded_file, df: pd.DataFrame | None, required_columns: list[str]):
    if not uploaded_file:
        st.info("No file uploaded yet.")
        return False

    st.caption(f"File: {uploaded_file.name}")
    if df is None:
        st.warning("Could not read this file.")
        return False

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    c3.metric("Required", len(required_columns))

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return False
    st.success("Required columns check passed.")
    return True






def export_to_excel(
    df: pd.DataFrame, 
    sheet_name: str = "Detailed Data", 
    additional_sheets: dict[str, pd.DataFrame] = None,
    report_title: str = "Business Intelligence Report",
    summary_metrics: dict[str, Any] = None
) -> bytes:
    """High-fidelity Excel export with professional styling, multi-sheet support, and summary insights."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1. Summary Sheet (If metrics provided)
        if summary_metrics:
            summary_df = pd.DataFrame([
                {"Metric": k, "Value": v} for k, v in summary_metrics.items()
            ])
            summary_df.to_excel(writer, index=False, sheet_name="Executive Summary")
        
        # 2. Main Data Sheet
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        
        # 3. Additional Sheets
        if additional_sheets:
            for s_name, s_df in additional_sheets.items():
                s_df.to_excel(writer, index=False, sheet_name=s_name)
        
        wb = writer.book
        
        # Consistent Styling
        header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        summary_fill = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'), 
            right=Side(style='thin', color='CBD5E1'), 
            top=Side(style='thin', color='CBD5E1'), 
            bottom=Side(style='thin', color='CBD5E1')
        )
        
        for ws in wb.worksheets:
            is_summary = ws.title == "Executive Summary"
            
            # Header Styling
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border
            
            # Freeze Header (except summary)
            if not is_summary:
                ws.freeze_panes = 'A2'
            
            # Auto-adjust column widths and apply borders
            for col_idx, col in enumerate(ws.columns, 1):
                max_length = 0
                column_letter = get_column_letter(col_idx)
                
                for cell in col:
                    # Styling every cell
                    cell.border = thin_border
                    if is_summary and cell.row > 1:
                        cell.fill = summary_fill
                        
                    try:
                        val_str = str(cell.value)
                        if len(val_str) > max_length:
                            max_length = len(val_str)
                    except:
                        pass
                
                ws.column_dimensions[column_letter].width = max(min(max_length + 3, 60), 12)

    output.seek(0)
    return output.read()

def render_ai_pilot_chat_ui(sales_df: pd.DataFrame, returns_df: pd.DataFrame = None, stock_df: pd.DataFrame = None, key_prefix: str = "global"):
    """Renders the AI Data Pilot chat interface inside a container like a popover."""
    st.markdown("#### 🤖 Operations Data Pilot")
    st.caption("Ask natural language questions about your e-commerce health.")

    chat_key = f"pilot_messages_{key_prefix}"

    # Initialize chat history in session state if it doesn't exist
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [{"role": "assistant", "content": "How can I help you analyze the data?"}]

    import re
    # Display prior chat messages
    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Re-render any historical Plotly charts detected
            if message["role"] == "assistant" and ("[TOOL_CALL: GENERATE_PLOTLY]" in message.get("content", "") or "[TOOL_CALL: EXECUTE_PYTHON]" in message.get("content", "")) and "```python" in message.get("content", ""):
                code_blocks = re.findall(r'```python\n(.*?)\n```', message["content"], re.DOTALL)
                for code in code_blocks:
                    try:
                        import duckdb
                        local_vars = {
                            "pd": pd, 
                            "duckdb": duckdb,
                            "sales_df": sales_df.copy() if isinstance(sales_df, pd.DataFrame) else pd.DataFrame(),
                            "returns_df": returns_df.copy() if isinstance(returns_df, pd.DataFrame) else pd.DataFrame(),
                            "stock_df": stock_df.copy() if isinstance(stock_df, pd.DataFrame) else pd.DataFrame(),
                            "export_df": None,
                            "df": sales_df.copy() if isinstance(sales_df, pd.DataFrame) else pd.DataFrame()
                        }
                        safe_code = code.replace("fig.show()", "")
                        exec(safe_code, globals(), local_vars)
                        if "fig" in local_vars:
                            st.plotly_chart(local_vars["fig"], use_container_width=True)
                        if "export_df" in local_vars and isinstance(local_vars["export_df"], pd.DataFrame) and not local_vars["export_df"].empty:
                            st.dataframe(local_vars["export_df"], use_container_width=True)
                            csv = local_vars["export_df"].to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Result CSV",
                                data=csv,
                                file_name=f"pilot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key=f"export_hist_{hash(code)}"
                            )
                    except Exception as e:
                        st.error(f"Could not render/execute code from history: {e}")

    # Accept user input
    if prompt := st.chat_input("e.g., 'What are my top 5 selling products?'", key=f"chat_input_{key_prefix}"):
        # Add user message to history and display it
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display a mock assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    from BackEnd.services.nlp_engine import get_nlp_response
                    
                    import os
                    # Upgrade to prefer RAG Agent (Deep Data) as the default for agentic capability
                    agent_type = "RAG Agent (Deep Data)"
                    try:
                        if "GEMINI_API_KEY" in st.secrets or os.environ.get("GEMINI_API_KEY"):
                            pass # Default to RAG Agent which uses Gemini
                        elif "GROQ_API_KEY" in st.secrets or os.environ.get("GROQ_API_KEY"):
                            agent_type = "Groq"
                        elif "HUGGINGFACE_API_KEY" in st.secrets or os.environ.get("HUGGINGFACE_API_KEY"):
                            agent_type = "HuggingFace"
                        elif "OPENROUTER_API_KEY" in st.secrets or os.environ.get("OPENROUTER_API_KEY"):
                            agent_type = "OpenRouter"
                    except Exception:
                        agent_type = "Standard"
                    
                    response = get_nlp_response(prompt, sales_df, returns_df=returns_df, stock_df=stock_df, agent_type=agent_type)
                except Exception as e:
                    response = f"Sorry, I encountered an error during analysis: {e}"
                
                def stream_data(text):
                    import time
                    for word in text.split(" "):
                        yield word + " "
                        time.sleep(0.015)
                st.write_stream(stream_data(response))
                
                # Execute any newly generated Python code (Plotly / DuckDB / Pandas)
                if ("[TOOL_CALL: GENERATE_PLOTLY]" in response or "[TOOL_CALL: EXECUTE_PYTHON]" in response) and "```python" in response:
                    code_blocks = re.findall(r'```python\n(.*?)\n```', response, re.DOTALL)
                    for code in code_blocks:
                        try:
                            import duckdb
                            local_vars = {
                                "pd": pd,
                                "duckdb": duckdb,
                                "sales_df": sales_df.copy() if isinstance(sales_df, pd.DataFrame) else pd.DataFrame(),
                                "returns_df": returns_df.copy() if isinstance(returns_df, pd.DataFrame) else pd.DataFrame(),
                                "stock_df": stock_df.copy() if isinstance(stock_df, pd.DataFrame) else pd.DataFrame(),
                                "export_df": None,
                                "df": sales_df.copy() if isinstance(sales_df, pd.DataFrame) else pd.DataFrame()
                            }
                            safe_code = code.replace("fig.show()", "")
                            exec(safe_code, globals(), local_vars)
                            
                            if "fig" in local_vars:
                                st.plotly_chart(local_vars["fig"], use_container_width=True)
                                
                            if "export_df" in local_vars and isinstance(local_vars["export_df"], pd.DataFrame) and not local_vars["export_df"].empty:
                                st.dataframe(local_vars["export_df"], use_container_width=True)
                                csv = local_vars["export_df"].to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 Download Result CSV",
                                    data=csv,
                                    file_name=f"pilot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key=f"export_live_{hash(code)}"
                                )
                        except Exception as e:
                            st.error(f"Execution Error: {e}")
                
                st.feedback("thumbs", key=f"feedback_{len(st.session_state[chat_key])}")
        
        # Add assistant response to history
        st.session_state[chat_key].append({"role": "assistant", "content": response})


def show_last_updated(path: str):
    if not os.path.exists(path):
        return
    updated = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {updated}")
