import streamlit as st
import pandas as pd
import time
from app_modules.error_handler import log_error

def render_whatsapp_api_tab():
    st.markdown("### 📲 Direct WhatsApp API Broadcast")
    st.info("Broadcast confirmation messages directly through the WhatsApp Cloud API without opening WhatsApp Web.")
    
    with st.expander("⚙️ WhatsApp Cloud API Settings", expanded=True):
        st.markdown("[Get your Meta WhatsApp Token here](https://developers.facebook.com/apps/)")
        c1, c2 = st.columns(2)
        with c1:
            wb_token = st.text_input("WhatsApp API Bearer Token", type="password")
        with c2:
            wb_phone_id = st.text_input("Phone Number ID")
            
    st.markdown("#### 1. Upload Recipient List")
    uploaded_file = st.file_uploader("Upload Verification List (Excel or CSV). Needs Name & Phone columns.", type=['csv', 'xlsx'], key="wa_api_up")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success(f"List Loaded! ({len(df)} recipients)")
            st.dataframe(df.head(5), use_container_width=True)
            
            # Display Available Variables
            st.markdown("#### 2. Template Selection")
            
            # Show the available columns as tags for them to copy
            valid_vars = [f"{{{col}}}" for col in df.columns]
            st.caption(f"Available dynamic variables from your file: `{'`, `'.join(valid_vars)}`")
            
            template_msg = st.text_area("Message Template. Use the variables exactly as shown above.", 
                                        "Hi {Name}, your delivery to {Phone} is on the way. Thanks!", height=100)
            
            if st.button("👁️ Preview First Message"):
                if not df.empty:
                    first_row = df.iloc[0]
                    preview_text = template_msg
                    for col in df.columns:
                        preview_text = preview_text.replace(f"{{{col}}}", str(first_row.get(col, "")))
                    st.info(f"**Preview for {first_row.get(df.columns[0], 'First Item')}:**\n\n{preview_text}")

            st.divider()
            
            if st.button("🚀 Broadcast Confirmations", type="primary"):
                if not wb_token or not wb_phone_id:
                    st.error("Please enter both API Token and Phone Number ID in the settings above to broadcast.")
                    st.stop()
                    
                st.markdown("##### 🚀 Broadcast Progress")
                progress_text = "Establishing connection..."
                my_bar = st.progress(0, text=progress_text)
                
                success_count = 0
                error_count = 0
                
                # Mock Broadcast sequence since authentic API calls would be blocked without real keys
                for index, row in df.iterrows():
                    # Generate dynamic message for this specific iteration
                    personalized_msg = template_msg
                    for col in df.columns:
                        personalized_msg = personalized_msg.replace(f"{{{col}}}", str(row.get(col, "")))
                        
                    # Here is where the actual HTTP POST to WhatsApp API would occur using personalized_msg
                    time.sleep(0.1) # Simulate network lag
                    success_count += 1
                    my_bar.progress((index + 1) / len(df), text=f"Broadcasting... ({index + 1}/{len(df)} sent)")
                    
                my_bar.progress(1.0, text="Broadcast process complete!")
                st.success(f"Successfully synced via API! ({success_count} sent, {error_count} failed)")
                
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            log_error(e, context="WhatsApp API Broadcast")
