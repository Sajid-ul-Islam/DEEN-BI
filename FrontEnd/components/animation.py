import streamlit as st

def lottie_empty_state(message="No data available", height=300):
    html = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: {height}px; font-family: 'Inter', sans-serif; color: #64748b;">
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <lottie-player src="https://lottie.host/c5e5cc40-8f9f-43fb-a870-ab944f77cda6/1dEItiH2zX.json" background="transparent" speed="1" style="width: 150px; height: 150px;" loop autoplay></lottie-player>
        <div style="margin-top: 15px; font-weight: 600; font-size: 1rem; color: #94a3b8;">{message}</div>
    </div>
    """
    st.html(html)

def lottie_search_state(message="No results found", height=300):
    html = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: {height}px; font-family: 'Inter', sans-serif; color: #64748b;">
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <lottie-player src="https://lottie.host/1c8f1e62-c148-43d9-9524-7cbabf881273/9XjQGzP0kO.json" background="transparent" speed="1" style="width: 150px; height: 150px;" loop autoplay></lottie-player>
        <div style="margin-top: 15px; font-weight: 600; font-size: 1rem; color: #94a3b8;">{message}</div>
    </div>
    """
    st.html(html)
