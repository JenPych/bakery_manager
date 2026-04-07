import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid

# --- 1. DATA PERSISTENCE (GOOGLE SHEETS) ---


# Establish the connection
conn = st.connection("gsheets", type=GSheetsConnection)

conn.read(worksheet="Market Prices")

def save_all_to_sheets():
    """Converts session state to a flat dataframe and pushes to Google Sheets."""
    rows = []
    for r in st.session_state.master_records:
        inf = r["Info"]
        # Product Header Row
        rows.append({
            "Item": f"PRODUCT: {inf['Name']}", "Qty": 0, "Unit": "", "Price/Unit": 0,
            "Total Cost": inf.get('Total Cost', 0), "Raw Mat/Unit": inf.get('Raw Mat/Unit', 0),
            "Yield": inf.get('Yield', 1.0), "Waste %": inf.get('Waste %', 0),
            "MRP": inf.get('MRP', 0), "Margin %": inf.get('Margin %', 0),
            "OH Alloc %": inf.get('OH Alloc %', 100), "Pkg/Unit": inf.get('Pkg/Unit', 0)
        })
        # Ingredient Rows
        for ig in r["Recipe"]:
            rows.append({
                "Item": ig['item'], "Qty": ig['qty'], "Unit": ig['unit'],
                "Price/Unit": ig['price_per_unit'],
                "Total Cost": round(float(ig['qty']) * float(ig['price_per_unit']), 2),
                "Raw Mat/Unit": 0, "Yield": 0, "Waste %": 0, "MRP": 0, "Margin %": 0,
                "OH Alloc %": 0, "Pkg/Unit": 0
            })

    df = pd.DataFrame(rows)

    # Update the "Master Data" worksheet in your Google Sheet
    conn.update(worksheet="Master Data", data=df)
    st.success("✅ Database Synced to Google Sheets!")


def load_persistence():
    """Reads the Google Sheet and reconstructs the session state."""
    try:
        df = conn.read(worksheet="Master Data", ttl=0)  # ttl=0 ensures fresh data
        if df.empty: return False

        temp_recs = []
        curr_prod = None

        for _, row in df.iterrows():
            item_str = str(row.get('Item', '')).strip()
            if "PRODUCT:" in item_str:
                curr_prod = {
                    "Info": {
                        "Name": item_str.replace("PRODUCT:", "").strip(),
                        "Raw Mat/Unit": float(row.get('Raw Mat/Unit', 0)),
                        "Yield": float(row.get('Yield', 1.0)),
                        "Waste %": float(row.get('Waste %', 0)),
                        "MRP": float(row.get('MRP', 0)),
                        "Margin %": float(row.get('Margin %', 0)),
                        "OH Alloc %": float(row.get('OH Alloc %', 100)),
                        "Pkg/Unit": float(row.get('Pkg/Unit', 0)),
                        "Total Cost": float(row.get('Total Cost', 0)),
                        "VAT On": True
                    },
                    "Recipe": []
                }
                temp_recs.append(curr_prod)
            elif curr_prod and item_str:
                curr_prod["Recipe"].append({
                    "item": item_str,
                    "qty": float(row.get('Qty', 0)),
                    "unit": str(row.get('Unit', 'g')),
                    "price_per_unit": float(row.get('Price/Unit', 0))
                })

        st.session_state.master_records = temp_recs
        return True
    except Exception as e:
        st.error(f"Failed to load from Sheets: {e}")
        return False


# --- 2. UTILITIES & APP ENGINE ---
def rd(v):
    try:
        return round(float(v), 2)
    except:
        return 0.0


def bagels_co_master_engine():
    st.set_page_config(page_title="Bagels & Co. | Cloud Engine", layout="wide")

    if 'initialized' not in st.session_state:
        st.session_state.master_records = []
        load_persistence()  # Attempt to load from Cloud on startup
        st.session_state.price_dict = {}  # You can also move prices to a Google Sheet tab!
        st.session_state.overheads = {
            "rent": 150000.0, "salaries": 150000.0, "utilities": 50000.0,
            "marketing": 10000.0, "assets": 2000000.0, "dep_years": 5, "monthly_units": 2000
        }
        st.session_state.editing_name = "New Item"
        st.session_state.load_id = 0
        st.session_state.recipe_buffer = [
            {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
        st.session_state.current_strategy = {"Yield": 1.0, "Waste %": 5.0, "Pkg/Unit": 15.0, "OH Alloc %": 100,
                                             "Margin %": 50.0, "VAT On": True}
        st.session_state.initialized = True

    st.title("🥯 Bagels & Co. | Cloud Business Engine")

    # [Rest of your UI logic (Recipe Construction, Strategy, Summary) remains exactly the same]

    # --- UPDATED SAVE BUTTON ---
    if st.button("💾 SAVE & SYNC TO GOOGLE SHEETS", type="primary", use_container_width=True):
        # ... [Your logic to update st.session_state.master_records] ...
        # (Same as your previous script)

        save_all_to_sheets()
        st.rerun()


if __name__ == "__main__":
    bagels_co_master_engine()