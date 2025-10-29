import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Page setup
st.set_page_config(layout="wide")
st.title("Trade History & P/L")

# --- 1. GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA LOADING (Now reads 16 columns) ---
@st.cache_data(ttl=60)
def load_inventory():
    """Reads all data from the 'Trades' tab."""
    try:
        data = conn.read(
            worksheet="Trades",
            usecols=list(range(16)), # Reads all 16 columns
            header=0
        )
        data = data.dropna(how="all")
        # Convert types for correct calculations
        data['Price_Bought'] = pd.to_numeric(data['Price_Bought'])
        data['P_L'] = pd.to_numeric(data['P_L'])
        data['ROI'] = pd.to_numeric(data['ROI'])
        return data
    except Exception as e:
        st.error(f"Error reading from Google Sheet. Exception Type: {type(e)}. Full Error: {repr(e)}")
        return pd.DataFrame()

# Load all data
inventory_df = load_inventory()

# --- 3. DISPLAY SOLD ITEMS & P/L ---
st.header("Sold Items")

if not inventory_df.empty:
    # Filter for items that ARE sold
    sold_items = inventory_df.dropna(subset=['Date_Sold'])
    
    if not sold_items.empty:
        # --- 4. P/L SUMMARY (Now with ROI) ---
        total_profit = sold_items['P_L'].sum()
        total_trades = len(sold_items)
        avg_roi = sold_items['ROI'].mean()
        
        st.subheader("📈 P/L Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Profit", f"${total_profit:,.2f}")
        col2.metric("Completed Trades", total_trades)
        col3.metric("Average ROI", f"{avg_roi:.2f}%")
        
        st.divider()

        # Define columns to show
        display_columns = [
            "Skin_Name", "Buyer", "Date_Bought", "Date_Sold",
            "Price_Bought", "Price_Sold", "Sell_Fee", "P_L", "ROI"
        ]
        
        # --- THIS IS THE UPDATED SECTION ---
        st.dataframe(
            sold_items[display_columns], 
            use_container_width=True,
            column_config={
                "ROI": st.column_config.NumberColumn(
                    "ROI (%)",  # Set a nice header
                    format="%.2f%%", # Format as percentage with 2 decimals
                )
            }
        )

    else:
        st.info("You have not sold any items yet.")
else:
    st.info("No items have been logged yet.")