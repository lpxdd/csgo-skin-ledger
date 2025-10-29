import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Page setup
st.set_page_config(layout="wide")
st.title("Sell an Item")

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
        data['Price_Bought'] = pd.to_numeric(data['Price_Bought'])
        data['Market_Price_Estimate'] = pd.to_numeric(data['Market_Price_Estimate'])
        return data
    except Exception as e:
        st.error(f"Error reading from Google Sheet. Exception Type: {type(e)}. Full Error: {repr(e)}")
        return pd.DataFrame()

# Load all data
inventory_df = load_inventory()

if not inventory_df.empty:
    # We must filter for inventory items first, so the dropdown can be created
    inventory_items = inventory_df[pd.isna(inventory_df["Date_Sold"]) | (inventory_df["Date_Sold"] == "")]
    
    if not inventory_items.empty:
        
        # --- 4. THE "SELL ITEM" FORM (MOVED TO TOP) ---
        st.header("Log a Sale")
        
        # Create a list of items to sell (Name + ID)
        sellable_items_list = [
            f"{row['Skin_Name']} (ID: {row['Trade_ID']})" 
            for index, row in inventory_items.iterrows()
        ]
        
        selected_item_to_sell = st.selectbox(
            "Select item to sell:",
            options=sellable_items_list,
            index=None,
            placeholder="Select a skin from your inventory..."
        )
        
        if selected_item_to_sell:
            with st.form("sell_form", clear_on_submit=True):
                st.write(f"**Selling:** {selected_item_to_sell}")
                
                # --- THIS IS THE FIX ---
                price_sold = st.number_input("Price Sold ($)", min_value=0.0, step=0.01, value=None)
                sell_fee = st.number_input("Sell Fee ($)", min_value=0.0, step=0.01, value=None)
                # --- END FIX ---
                
                platform_sold = st.selectbox("Platform Sold", options=["CSGOEmpire", "CSGORoll", "Steam Market", "Other"])
                
                sell_button = st.form_submit_button("Confirm Sale")
            
            if sell_button:
                try:
                    trade_id_to_sell = selected_item_to_sell.split(" (ID: ")[-1].replace(")", "")
                    item_row = inventory_items.loc[inventory_items['Trade_ID'] == trade_id_to_sell].iloc[0]
                    price_bought_val = item_row['Price_Bought']
                    
                    # --- THIS IS THE FIX (Handles the 'None' value) ---
                    price_sold_val = price_sold if price_sold is not None else 0.0
                    sell_fee_val = sell_fee if sell_fee is not None else 0.0
                    # --- END FIX ---
                    
                    # Calculate P/L and ROI
                    profit_loss = (price_sold_val - sell_fee_val) - price_bought_val
                    roi_val = (profit_loss / price_bought_val) * 100 if price_bought_val != 0 else 0
                    
                    date_sold_val = datetime.now().date().isoformat()
                    
                    # 1. Access the wrapper client
                    wrapper_client = conn._raw_instance
                    real_gspread_client = wrapper_client._optional_client
                    
                    # 2. Open the spreadsheet and worksheet
                    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    sh = real_gspread_client.open_by_url(spreadsheet_url)
                    worksheet = sh.worksheet("Trades")
                    
                    # 3. Find the row to update
                    cell = worksheet.find(trade_id_to_sell)
                    row_to_update = cell.row
                    
                    # 4. Update the cells in that row (Cols K-P)
                    worksheet.update_cell(row=row_to_update, col=11, value=platform_sold) # Platform_Sold
                    worksheet.update_cell(row=row_to_update, col=12, value=date_sold_val) # Date_Sold
                    worksheet.update_cell(row=row_to_update, col=13, value=price_sold_val)   # Price_Sold
                    worksheet.update_cell(row=row_to_update, col=14, value=sell_fee_val)     # Sell_Fee
                    worksheet.update_cell(row=row_to_update, col=15, value=profit_loss)  # P_L
                    worksheet.update_cell(row=row_to_update, col=16, value=roi_val)       # ROI

                    st.success(f"Sold! P/L: ${profit_loss:.2f} (ROI: {roi_val:.2f}%)")
                    st.cache_data.clear()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error updating sheet: {repr(e)}")

        st.divider() # Add a line to separate sections
        
        # --- 3. DISPLAY CURRENT INVENTORY (MOVED TO BOTTOM) ---
        st.header("Current Inventory")
        st.write("This is everything you own that has not been sold.")
        
        display_columns = [
            "Trade_ID", "Skin_Name", "Buyer", "Price_Bought", 
            "Tradable_On", "Platform_Bought"
        ]
        st.dataframe(inventory_items[display_columns], use_container_width=True)

    else:
        # This 'else' belongs to 'if not inventory_items.empty:'
        st.info("Your inventory is currently empty. Log a new purchase to get started.")
else:
    # This 'else' belongs to 'if not inventory_df.empty:'
    st.info("No items have been logged yet.")