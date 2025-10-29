import streamlit as st
import pandas as pd
import requests
import uuid
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Page setup
st.set_page_config(layout="wide")

# --- 0. CONSTANTS ---
SKIN_CONDITIONS = [
    "Factory New", "Minimal Wear", "Field-Tested", 
    "Well-Worn", "Battle-Scarred", "Not Applicable"
]
BUYERS = ["LP", "GGE", "TOM"]
PLATFORMS = ["CSGOEmpire", "CSGORoll", "Steam Market", "Other"]

# --- 1. GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA LOADING (The "Skin Bank") ---
@st.cache_data(ttl=86400)
def load_skin_data():
    """Downloads skin data from the ByMykel CSGO-API and processes it."""
    try:
        url = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        processed_skins = {}
        for item in data:
            if item.get('rarity') and item.get('weapon'):
                full_name = f"{item['weapon']['name']} | {item['name']}"
                skin_id = item['id']
                image_url = item['image']
                
                processed_skins[skin_id] = {
                    'name': full_name,
                    'image_url': image_url
                }
        return processed_skins
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading skin API: {e}")
        return None

# --- 3. THE STREAMLIT APP UI ---
st.title("🗃️ CS:GO Skin Ledger")
st.header("Log a New Purchase")

skin_data = load_skin_data()

if skin_data:
    skin_name_list = [f"{details['name']} (ID: {skin_id})" for skin_id, details in skin_data.items()]
    
    selected_skin_formatted = st.selectbox(
        label="Select a Skin to Log:",
        options=skin_name_list,
        index=None,
        placeholder="Type to search for a skin (e.g., 'AK-47 Redline')..."
    )
    
    if selected_skin_formatted:
        selected_id = selected_skin_formatted.split("(ID: ")[-1].replace(")", "")
        selected_skin_details = skin_data[selected_id]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader(selected_skin_details['name'])
            st.image(selected_skin_details['image_url'], use_container_width=True)
            st.caption(f"Internal Skin ID: `{selected_id}`")

        with col2:
            st.subheader("Purchase Details")
            
            with st.form(key="new_purchase_form", clear_on_submit=True):
                condition = st.selectbox("Condition", options=SKIN_CONDITIONS)
                is_stattrak = st.checkbox("StatTrak™")
                
                # --- THIS IS THE FIX ---
                price_bought = st.number_input("Price Bought ($)", min_value=0.0, step=0.01, value=None)
                market_price = st.number_input("Market Price Estimate ($)", min_value=0.0, step=0.01, value=None)
                # --- END FIX ---
                
                platform_bought = st.selectbox("Platform Bought", options=PLATFORMS)
                buyer = st.selectbox("Buyer", options=BUYERS)
                submit_button = st.form_submit_button(label="Add to Inventory")

            if submit_button:
                try:
                    today = datetime.now().date()
                    tradeable_date = today + timedelta(days=7)
                    trade_id = f"T-{str(uuid.uuid4())[:8]}"
                    
                    st_prefix = "StatTrak™ " if is_stattrak else ""
                    condition_suffix = f" ({condition})" if condition != "Not Applicable" else ""
                    full_display_name = f"{st_prefix}{selected_skin_details['name']}{condition_suffix}"

                    # --- THIS IS THE FIX (Handles the 'None' value) ---
                    price_bought_val = price_bought if price_bought is not None else 0.0
                    market_price_val = market_price if market_price is not None else 0.0
                    # --- END FIX ---

                    # Prepare data as a list in the correct column order
                    new_row_list = [
                        trade_id, today.isoformat(), tradeable_date.isoformat(),
                        selected_id, full_display_name, condition, is_stattrak,
                        platform_bought, price_bought_val, market_price_val, buyer,
                        None, None, None, None, None  # Date_Sold, Price_Sold, Sell_Fee, P_L, ROI
                    ]
                    
                    # 1. Access the raw gspread client
                    client = conn._raw_instance
                    real_gspread_client = client._optional_client
                    
                    # 2. Open the sheet and worksheet
                    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    sh = real_gspread_client.open_by_url(spreadsheet_url)
                    worksheet = sh.worksheet("Trades")
                    
                    # 3. Append the new row
                    worksheet.append_row(new_row_list)
                    
                    st.success(f"Success! Added: {full_display_name}")
                    st.cache_data.clear() # Clear cache so other pages see the new item
                
                except Exception as e:
                    st.error(f"Error saving to Google Sheet. Exception Type: {type(e)}. Full Error: {repr(e)}")
else:
    st.error("Could not load skin data. The app cannot proceed.")