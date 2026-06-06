import streamlit as st

@st.dialog("🔍 Command Palette")
def render_command_palette():
    st.markdown("""
        <style>
        [data-testid="stDialog"] {
            border-radius: 16px !important;
            padding: 0 !important;
            overflow: hidden !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    query = st.text_input("Type a command, customer name, or order ID...", key="cmd_palette_input", label_visibility="collapsed", placeholder="e.g., Go to Stock Insights, or #12345")
    
    if query:
        query_lower = query.lower()
        if "stock" in query_lower or "inventory" in query_lower:
            st.session_state.active_section = "📦 Stock Insight"
            st.rerun()
        elif "return" in query_lower:
            st.session_state.active_section = "🔄 Returns Insights"
            st.rerun()
        elif "customer" in query_lower:
            st.session_state.active_section = "👥 Customer Insight"
            st.rerun()
        elif "sales" in query_lower:
            st.session_state.active_section = "💎 Sales Overview"
            st.rerun()
        else:
            from FrontEnd.components.animation import lottie_search_state
            lottie_search_state(f"Searching across database for '{query}'...")
    else:
        st.markdown("### Quick Links")
        c1, c2, c3 = st.columns(3)
        if c1.button("💎 Sales Overview", use_container_width=True):
            st.session_state.active_section = "💎 Sales Overview"
            st.rerun()
        if c2.button("📦 Stock Insights", use_container_width=True):
            st.session_state.active_section = "📦 Stock Insight"
            st.rerun()
        if c3.button("🔄 Returns Insights", use_container_width=True):
            st.session_state.active_section = "🔄 Returns Insights"
            st.rerun()

def inject_command_palette_listener():
    # Invisible button to trigger the dialog
    if st.button("Open Palette", key="hidden_cmd_btn", help="Hidden button for Ctrl+K"):
        render_command_palette()
        
    st.markdown("""
        <style>
        /* Hide the trigger button */
        button[title="Hidden button for Ctrl+K"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    import streamlit.components.v1 as components
    components.html("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const buttons = Array.from(doc.querySelectorAll('button'));
                const btn = buttons.find(b => b.title === 'Hidden button for Ctrl+K');
                if (btn) btn.click();
            }
        });
        </script>
    """, height=0, width=0)
