import streamlit as st
import pandas as pd
from io import BytesIO


def bagels_co_v11():
    st.set_page_config(page_title="Bagels & Co. | Master Engine", layout="wide")

    # --- 1. SESSION STATE ---
    if 'master_records' not in st.session_state: st.session_state.master_records = []
    if 'price_dict' not in st.session_state: st.session_state.price_dict = {}
    if 'editing_name' not in st.session_state: st.session_state.editing_name = "New Item"
    if 'load_id' not in st.session_state: st.session_state.load_id = 0
    if 'recipe_buffer' not in st.session_state:
        st.session_state.recipe_buffer = [{"item": "", "qty": 0.0, "unit": "g", "price": 0.0, "search_version": 0}]

    def rd(v):
        try:
            return round(float(v), 2)
        except:
            return 0.0

    # --- 2. SIDEBAR: DATA MANAGEMENT (RE-ADDED RESTORE) ---
    st.sidebar.header("📁 Data Management")

    # SYNC PRICES
    price_file = st.sidebar.file_uploader("1. Sync Market Prices", type=["xlsx", "csv"])
    if price_file and st.sidebar.button("🔄 Update Market Prices"):
        try:
            df_raw = pd.read_excel(price_file) if price_file.name.endswith('.xlsx') else pd.read_csv(price_file)
            actual_data = None
            for i in range(len(df_raw)):
                row_vals = [str(val) for val in df_raw.iloc[i].values]
                if any("Ingredient Name" in v for v in row_vals):
                    df_raw.columns = df_raw.iloc[i]
                    actual_data = df_raw.iloc[i + 1:].copy()
                    break
            if actual_data is not None:
                new_lib = {str(row.get('Ingredient Name', '')).strip().lower(): rd(row.get('Price per Unit', 0))
                           for _, row in actual_data.iterrows() if str(row.get('Ingredient Name', '')) != "nan"}
                st.session_state.price_dict = new_lib
                st.sidebar.success(f"✅ {len(new_lib)} Prices Synced!")
        except Exception as e:
            st.sidebar.error(f"Sync failed: {e}")

    # RESTORE DATABASE (FIXED)
    restore_file = st.sidebar.file_uploader("2. Restore Master List", type=["xlsx", "csv"])
    if restore_file and st.sidebar.button("📂 Run Full Restore"):
        try:
            df_res = pd.read_excel(restore_file) if restore_file.name.endswith('.xlsx') else pd.read_csv(restore_file)
            df_res = df_res.fillna("")
            temp_recs, curr_prod = [], None
            for _, row in df_res.iterrows():
                item_str = str(row.get('Item', '')).strip()
                if "--- PRODUCT:" in item_str:
                    p_name = item_str.replace("--- PRODUCT:", "").replace("---", "").strip()
                    curr_prod = {
                        "Info": {
                            "Name": p_name,
                            "Raw Mat/Unit": rd(row.get('Raw Mat/Unit', 0)),
                            "Yield": rd(row.get('Yield', 1.0)),
                            "Waste %": rd(row.get('Waste %', 0)),
                            "MRP": rd(row.get('MRP', 0)),
                            "Margin %": rd(row.get('Margin %', 0)),
                            "OH Alloc %": rd(row.get('OH Alloc %', 100)),
                            "Total Cost": rd(row.get('Total Cost', 0))
                        },
                        "Recipe": []
                    }
                    temp_recs.append(curr_prod)
                elif curr_prod and item_str and not item_str.startswith("---") and item_str != "":
                    curr_prod["Recipe"].append(
                        {"item": item_str, "qty": rd(row.get('Qty', 0)), "unit": str(row.get('Unit', 'g')),
                         "price_per_unit": rd(row.get('Price/Unit', 0))})
            st.session_state.master_records = temp_recs
            st.sidebar.success("✅ Database & Strategies Restored!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Restore Error: {e}")

    # --- 3. TOP NAVIGATION ---
    st.title("Bagels & Co. | Master Business Engine")
    n1, n2 = st.columns([2, 1])
    with n1:
        if st.session_state.master_records:
            names = sorted(list(set(r["Info"]["Name"] for r in st.session_state.master_records)))
            sel = st.selectbox("📂 Load Product", ["-- Select --"] + names)
            if st.button("📂 Open Product") and sel != "-- Select --":
                record = next(r for r in st.session_state.master_records if r["Info"]["Name"] == sel)
                st.session_state.recipe_buffer = [
                    {"item": i['item'], "qty": i['qty'], "unit": i['unit'], "price": i['price_per_unit'],
                     "search_version": 0} for i in record["Recipe"]]
                st.session_state.editing_name = record["Info"]["Name"]
                st.session_state.load_id += 1
                st.rerun()
    with n2:
        st.write("---")
        if st.button("➕ Create New Product", use_container_width=True):
            st.session_state.recipe_buffer = [{"item": "", "qty": 0.0, "unit": "g", "price": 0.0, "search_version": 0}]
            st.session_state.editing_name = "New Item"
            st.session_state.load_id += 1
            st.rerun()

    st.divider()

    # --- 4. FIXED OVERHEADS ---
    with st.expander("🏢 Monthly Business Overheads"):
        o1, o2, o3 = st.columns(3)
        rent, sals, utils = o1.number_input("Rent", 0.0, value=159000.0), o2.number_input("Salaries", 0.0,
                                                                                         value=120000.0), o3.number_input(
            "Utilities", 0.0, value=50000.0)
        o4, o5, o6 = st.columns(3)
        ads, assets, units = o4.number_input("Marketing", 0.0, value=5000.0), o5.number_input("Asset Value", 0.0,
                                                                                              value=1900000.0), o6.number_input(
            "Total Monthly Units", 1.0, value=2000.0)
        dep_years = st.slider("Asset Depreciation Years", 1, 20, 5)
        avg_oh_per_unit = rd((rent + sals + utils + ads + (assets / (dep_years * 12))) / units)
        st.info(f"Average System Overhead/Unit: **रू {avg_oh_per_unit:.2f}**")

    # --- 5. RECIPE EDITOR ---
    prod_name = st.text_input("Product Name", value=st.session_state.editing_name,
                              key=f"pname_{st.session_state.load_id}")
    new_buffer = []
    for i, row in enumerate(st.session_state.recipe_buffer):
        cols = st.columns([2.5, 1, 1, 1.2, 1.2, 0.5])
        v, lid = row.get('search_version', 0), st.session_state.load_id
        name = cols[0].text_input("Item", value=row['item'], key=f"n_{i}_{v}_{lid}")
        qty = cols[1].number_input("Qty", min_value=0.0, value=float(row['qty']), key=f"q_{i}_{v}_{lid}")
        unit = cols[2].selectbox("Unit", ["g", "kg", "ml", "ltr", "pcs"], index=0, key=f"u_{i}_{v}_{lid}")
        price = cols[3].number_input("Price/Unit", min_value=0.0, value=float(row['price']), key=f"p_{i}_{v}_{lid}")
        row_total = rd(qty * price)
        cols[4].write(f"रू {row_total:.2f}")
        if cols[5].button("🔍", key=f"btn_{i}_{lid}"):
            lookup = name.strip().lower()
            if lookup in st.session_state.price_dict:
                st.session_state.recipe_buffer[i] = {"item": name, "qty": qty, "unit": unit,
                                                     "price": st.session_state.price_dict[lookup],
                                                     "search_version": v + 1}
                st.rerun()
        new_buffer.append(
            {"item": name, "qty": qty, "unit": unit, "price": price, "total": row_total, "search_version": v})
    st.session_state.recipe_buffer = new_buffer
    if st.button("➕ Add Row"):
        st.session_state.recipe_buffer.append({"item": "", "qty": 0.0, "unit": "g", "price": 0.0, "search_version": 0})
        st.rerun()

    # --- 6. CALCULATIONS ---
    st.divider()
    st.subheader("⚖️ Strategy & Pricing")
    f1, f2, f3 = st.columns(3)
    yld = f1.number_input("Yield", 0.01, value=1.0, key=f"yld_{st.session_state.load_id}")
    waste = f2.number_input("Waste %", 0.0, value=5.0, key=f"wst_{st.session_state.load_id}")
    pkg = f3.number_input("Pkg/Unit", 0.0, value=15.0, key=f"pkg_{st.session_state.load_id}")

    f4, f5 = st.columns(2)
    oh_alloc = f4.slider("Overhead Allocation %", 0, 200, 100, key=f"oha_{st.session_state.load_id}")
    margin_input = f5.number_input("Profit Margin %", 0.0, value=50.0, key=f"mgn_{st.session_state.load_id}")

    add_vat = st.checkbox("Include 13% VAT in MRP", value=True)

    applied_oh = rd(avg_oh_per_unit * (oh_alloc / 100))
    clean_recipe = [x for x in st.session_state.recipe_buffer if x['item'].strip() != ""]
    batch_raw = sum(x['total'] for x in clean_recipe)
    batch_waste = rd(batch_raw / (1 - (waste / 100))) if waste < 100 else batch_raw
    raw_mat_per_unit = rd(batch_waste / yld)
    final_cost = rd(raw_mat_per_unit + applied_oh + pkg)

    price_before_vat = rd(final_cost / (1 - (margin_input / 100))) if margin_input < 100 else final_cost
    mrp = rd(price_before_vat * 1.13) if add_vat else price_before_vat

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Raw Material", f"रू {raw_mat_per_unit}")
    c2.metric("Overhead", f"रू {applied_oh}")
    c3.metric("Total Cost", f"रू {final_cost}")
    c4.metric("Final MRP", f"रू {mrp}")

    if st.button("💾 Save Product & Strategy", type="primary"):
        entry = {"Info": {"Name": prod_name, "Raw Mat/Unit": raw_mat_per_unit, "MRP": mrp, "Margin %": margin_input,
                          "OH Alloc %": oh_alloc, "Yield": yld, "Waste %": waste, "Total Cost": batch_waste},
                 "Recipe": [{"item": i['item'], "qty": i['qty'], "unit": i['unit'], "price_per_unit": i['price']} for i
                            in clean_recipe]}
        idx = next((i for i, r in enumerate(st.session_state.master_records) if r["Info"]["Name"] == prod_name), None)
        if idx is not None:
            st.session_state.master_records[idx] = entry
        else:
            st.session_state.master_records.append(entry)
        st.success(f"✅ Strategy for '{prod_name}' saved to Database!")
        st.rerun()

    # --- 7. DATABASE VIEW ---
    if st.session_state.master_records:
        st.divider()
        st.subheader("📋 Master Database (Live View)")
        rows = []
        for r in st.session_state.master_records:
            inf = r["Info"]
            rows.append({
                "Item": f"--- PRODUCT: {inf['Name']} ---",
                "Qty": "", "Unit": "", "Price/Unit": "",
                "Total Cost": inf['Total Cost'],
                "Raw Mat/Unit": inf['Raw Mat/Unit'],
                "Yield": inf['Yield'],
                "Waste %": inf['Waste %'],
                "MRP": inf['MRP'],
                "Margin %": inf.get('Margin %', 0),
                "OH Alloc %": inf.get('OH Alloc %', 100)
            })
            for ig in r["Recipe"]:
                rows.append({
                    "Item": ig['item'], "Qty": ig['qty'], "Unit": ig['unit'],
                    "Price/Unit": ig['price_per_unit'],
                    "Total Cost": rd(ig['qty'] * ig['price_per_unit']),
                    "Raw Mat/Unit": "", "Yield": "", "Waste %": "", "MRP": "", "Margin %": "", "OH Alloc %": ""
                })

        df_view = pd.DataFrame(rows).astype(str).replace(["nan", "NaN", "None"], "")
        st.dataframe(df_view, use_container_width=True)

        out = BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            pd.DataFrame(rows).to_excel(writer, index=False, sheet_name='Costing_Summary')
        st.download_button("📥 Download Excel Database", out.getvalue(), "bagels_business_master.xlsx")


if __name__ == "__main__":
    bagels_co_v11()