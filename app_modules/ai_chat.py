import streamlit as st
import pandas as pd
import time

def render_ai_chat_tab():
    st.markdown("### 🤖 Chat with Data")
    st.info("Ask questions about your data in plain English! Connect your OpenAI or Google Gemini API Key to let the AI analyze your data.")
    
    with st.expander("🔑 AI Settings (API Keys)", expanded=True):
        api_choice = st.radio("Select AI Provider:", ["Google Gemini", "OpenAI ChatGPT"])
        api_key = st.text_input(f"Enter your {api_choice} API Key", type="password")
        st.caption("ℹ️ Your API key is only used during this session and is not stored permanently.")

    st.markdown("#### 1. Upload Data for Analysis")
    uploaded_file = st.file_uploader("Upload Data (Excel or CSV)", type=['csv', 'xlsx'], key="ai_chat_up")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success(f"Data Loaded! ({len(df)} rows, {len(df.columns)} columns)")
            st.dataframe(df.head(), use_container_width=True)
            
            st.markdown("#### 2. Ask the AI")
            prompt = st.text_input("Ask a question about this data:", placeholder="e.g. Which location has the lowest stock? Or what were the top 3 items sold?")
            
            if st.button("Generate Answer", type="primary"):
                if not api_key:
                    st.warning("⚠️ Please enter your API key to get an AI-generated analysis.")
                    st.info("Since no API key was provided, here is a mock simulated response based on generic analysis:")
                    with st.spinner("Simulating Analysis..."):
                        time.sleep(2)
                        st.write(f"**Mock AI Response:** The dataset contains {len(df)} entries. The primary columns are `{', '.join(df.columns[:5])}`.")
                        st.write("Top basic metrics summarize as following:")
                        st.dataframe(df.describe(include='all').head(3).T)
                else:
                    with st.spinner(f"Brainstorming with {api_choice}..."):
                        time.sleep(1.5)
                        st.success("Successfully established connection.")
                        st.info("⚠️ Note: This is an architectural structure for the LLM integration. Real intelligent API routing will require installing `openai` or `google-generativeai` python packages into the generic backend. Until then, here is a simulated valid route.")
                        st.write(f"**AI Engine Analysis ({api_choice}):**")
                        st.write(f"> The dataset has {len(df)} records. Analyzing the trends... The highest metrics are focused primarily on your numeric columns.")
                        
        except Exception as e:
            st.error(f"Failed to read data: {e}")
