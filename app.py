import streamlit as st

st.set_page_config(
    page_title="Automation Hub Pro",
    page_icon="AH",
    layout="wide",
    initial_sidebar_state="expanded",
)


def run_app():
    # Lazy imports keep bootstrap resilient on cloud when a module has runtime incompatibilities.
    from app_modules.ai_chat import render_ai_chat_tab
    from app_modules.bike_animation import render_bike_animation
    from app_modules.distribution_tab import render_distribution_tab
    from app_modules.error_handler import get_logs, log_error
    from app_modules.fuzzy_parser_tab import render_fuzzy_parser_tab
    from app_modules.more_tools import (
        render_daily_summary_export_tab,
        render_data_quality_monitor_tab,
    )
    from app_modules.pathao_tab import render_pathao_tab
    from app_modules.persistence import init_state, save_state
    from app_modules.sales_dashboard import render_live_tab, render_manual_tab
    from app_modules.ui_components import (
        inject_base_styles,
        render_header,
        sample_file_download,
        section_card,
    )
    from app_modules.ui_config import PRIMARY_NAV
    from app_modules.whatsapp_api import render_whatsapp_api_tab
    from app_modules.wp_tab import render_wp_tab

    init_state()
    inject_base_styles()

    with st.sidebar:
        st.subheader("Global Settings")
        st.session_state.low_stock_threshold = st.number_input(
            "Safety stock level",
            min_value=0,
            value=int(st.session_state.get("low_stock_threshold", 5)),
            step=1,
        )
        st.session_state.inv_matrix_search = st.text_input(
            "Inventory search (SKU/Name)",
            value=st.session_state.get("inv_matrix_search", ""),
        )
        st.session_state.guided_mode = st.toggle(
            "Guided workflow mode",
            value=st.session_state.get("guided_mode", True),
            help="Show step-by-step indicators in each workflow.",
        )
        st.session_state.show_animation = st.toggle(
            "Show motion effects",
            value=st.session_state.get("show_animation", False),
        )

        if st.button("Save session state", use_container_width=True):
            save_state()
            st.success("Session state saved.")

        with st.expander("Sample Templates", expanded=False):
            sample_file_download(
                "Download Pathao sample (CSV)",
                [
                    {
                        "Order Number": "1001",
                        "Phone (Billing)": "01700000000",
                        "First Name (Shipping)": "Customer One",
                        "Item Name": "Oxford Shirt",
                        "SKU": "OXF-M-BLU",
                        "Quantity": 1,
                        "State Name (Billing)": "Dhaka",
                        "Address 1&2 (Shipping)": "Mirpur 10",
                        "Payment Method Title": "Cash on delivery",
                        "Order Total Amount": 1200,
                    }
                ],
                "pathao_template.csv",
            )
            sample_file_download(
                "Download Inventory sample (CSV)",
                [{"Item Name": "Oxford Shirt", "Size": "M", "Quantity": 5, "SKU": "OXF-M-BLU"}],
                "inventory_template.csv",
            )
            sample_file_download(
                "Download WhatsApp sample (CSV)",
                [
                    {
                        "Phone (Billing)": "01700000000",
                        "Full Name (Billing)": "Customer One",
                        "Order ID": "1001",
                        "Product Name (main)": "Oxford Shirt",
                        "SKU": "OXF-M-BLU",
                        "Quantity": 1,
                        "Item cost": 1200,
                        "Order Total Amount": 1200,
                    }
                ],
                "whatsapp_template.csv",
            )

    if st.session_state.get("show_animation"):
        render_bike_animation()

    render_header()
    section_card(
        "How to use",
        "Follow each module workflow: Upload -> Validate -> Preview -> Export.",
    )

    nav_tabs = st.tabs(PRIMARY_NAV)

    with nav_tabs[0]:
        dashboard_tabs = st.tabs(["Live", "Manual Upload"])
        with dashboard_tabs[0]:
            render_live_tab()
        with dashboard_tabs[1]:
            render_manual_tab()

    with nav_tabs[1]:
        orders_tabs = st.tabs(["Pathao Processor", "Delivery Text Parser"])
        with orders_tabs[0]:
            render_pathao_tab(guided=st.session_state.get("guided_mode", True))
        with orders_tabs[1]:
            render_fuzzy_parser_tab(guided=st.session_state.get("guided_mode", True))

    with nav_tabs[2]:
        render_distribution_tab(
            search_q=st.session_state.get("inv_matrix_search", ""),
            guided=st.session_state.get("guided_mode", True),
        )

    with nav_tabs[3]:
        render_wp_tab(guided=st.session_state.get("guided_mode", True))

    with st.expander("More Tools", expanded=False):
        more_tabs = st.tabs(["System Logs", "Data Quality", "Daily Summary Export", "Dev Lab"])
        with more_tabs[0]:
            logs = get_logs()
            if logs:
                for entry in reversed(logs):
                    st.error(f"[{entry['timestamp']}] {entry['context']}: {entry['error']}")
            else:
                st.success("No errors recorded.")
        with more_tabs[1]:
            render_data_quality_monitor_tab()
        with more_tabs[2]:
            render_daily_summary_export_tab()
        with more_tabs[3]:
            dev_tabs = st.tabs(["AI Data Chat", "WhatsApp API Broadcast"])
            with dev_tabs[0]:
                render_ai_chat_tab()
            with dev_tabs[1]:
                render_whatsapp_api_tab()


try:
    run_app()
except Exception as exc:
    # Failsafe to prevent full redacted crash pages on Streamlit Cloud.
    from app_modules.error_handler import log_error

    log_error(exc, context="App Bootstrap")
    st.error("Application failed to render. Check 'More Tools -> System Logs' for details.")
    st.code(str(exc))
