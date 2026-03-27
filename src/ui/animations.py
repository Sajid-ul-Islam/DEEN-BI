import streamlit as st


def render_bike_animation():
    """Renders a premium motion effect for the background or accent."""
    motion_html = """
    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 4px; z-index: 9999; pointer-events: none;">
        <div style="width: 100%; height: 100%; background: linear-gradient(90deg, transparent, var(--neon-blue), transparent); 
                    background-size: 200% 100%; animation: shimmer 2s linear infinite;"></div>
    </div>
    <style>
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
    </style>
    """
    st.markdown(motion_html, unsafe_allow_html=True)

