import streamlit as st
import pandas as pd
from io import BytesIO
import copy


def ultimate_bakery_manager():
    st.set_page_config(page_title="Bakery & Café Master Pro", layout="wide")

    # --- 1. SESSION STATE (The Brain of the App) ---
    if 'master_records' not in st.session_state:
        st.session_state.master_records = []
    if 'ingredients' not in st.session_state:
        # We include 'version' to handle the widget refresh logic
        st.session_state.ingredients = [{"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0, "version": 0}]
    if 'price_dict' not in st.session_state:
        st.session_state.price_dict = {}
    if 'current_yield' not in st.session_state:
        st.session_state.current_yield = 1.0

    # --- 2. SIDEBAR CONTROLS ---
    st.sidebar.header("📁 Data Management")

    # PRICE LIST UPLOADER
    price_file = st.sidebar.file_uploader("1. Upload Market Price List (Excel)", type=["xlsx"])
    if price_file:
        try:
            raw_df = pd.read_excel(price_file, header=None).astype(str)
            h_row = 0
            for i, row in raw_df.head(10).iterrows():
                row_str = " ".join(row.values).lower()
                if any(x in row_str for x in ["ingredient", "price", "rate", "item"]):
                    h_row = i
                    break
            pdf = pd.read_excel(price_file, skiprows=h_row)
            cols = pdf.columns.tolist()
            n_col = next((c for c in cols if any(x in str(c).lower() for x in ["ingredient", "item", "name"])), None)
            p_col = next((c for c in cols if any(x in str(c).lower() for x in ["price", "rate", "cost"])), None)
            if n_col and p_col:
                if st.sidebar.button("🔄 Sync Market Prices"):
                    pdf[p_col] = pd.to_numeric(pdf[p_col], errors='coerce').fillna(0)
                    st.session_state.price_dict = {str(k).strip().lower(): round(float(v), 2)
                                                   for k, v in zip(pdf[n_col], pdf[p_col]) if str(k).lower() != 'nan'}
                    st.sidebar.success(f"✅ {len(st.session_state.price_dict)} Items Linked!")
        except Exception as e:
            st.sidebar.error(f"Sync Error: {e}")

    # MASTER LIST RESTORE
    restore_file = st.sidebar.file_uploader("2. Restore Master Records (Excel)", type=["xlsx"], key="rest_excel")
    if restore_file and st.sidebar.button("Restore Database"):
        try:
            df_res = pd.read_excel(restore_file).fillna("")
            temp_records = []
            curr_prod = None

            def sf(val):
                try:
                    return round(float(val), 2) if str(val) != "" else 0.0
                except:
                    return 0.0

            for _, row in df_res.iterrows():
                row_dict = row.to_dict()
                val = str(row.iloc[0]).strip()
                if "--- PRODUCT:" in val:
                    name = val.replace("--- PRODUCT: ", "").replace(" ---", "")
                    curr_prod = {"Product Info": {"Name": name, "Yield": sf(row_dict.get('Yield', 1.0)),
                                                  "Raw Mat/Unit": sf(
                                                      row_dict.get('Raw Mat/Unit', row_dict.get('Cost', 0))),
                                                  "MRP": sf(row_dict.get('MRP', 0))}, "Recipe": []}
                    temp_records.append(curr_prod)
                elif curr_prod and val and not val.startswith("---"):
                    curr_prod["Recipe"].append({"item": val, "qty": sf(row_dict.get('Qty', 0)),
                                                "unit": str(row_dict.get('Unit', 'g')).lower(),
                                                "price_per_unit": sf(row_dict.get('Price/Unit', 0)),
                                                "version": 0})
            st.session_state.master_records = temp_records
            st.sidebar.success("✅ Records Restored!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Restore Error: {e}")

    # --- 3. THE RECIPE EDITOR ---
    st.title("🥣 Bakery & Café Recipe Manager")

    prod_name = st.text_input("Product/Drink Name", value="New Item")
    st.divider()

    # DYNAMIC ROWS
    updated_ingredients = []
    for i, ing in enumerate(st.session_state.ingredients):
        # The key includes the 'version' so that clicking 'Get Price' resets the box
        v = ing.get('version', 0)
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1, 1, 1.5, 1, 1])

        # Inputs
        iname = c1.text_input("Ingredient", value=ing['item'], key=f"n_{i}_{v}")
        iqty = c2.number_input("Qty", value=float(ing['qty']), key=f"q_{i}_{v}", format="%.2f")

        unit_list = ["g", "kg", "ml", "ltr", "pcs"]
        u_idx = unit_list.index(ing.get('unit', 'g')) if ing.get('unit', 'g') in unit_list else 0
        iunit = c3.selectbox("Unit", unit_list, index=u_idx, key=f"u_{i}_{v}")

        iprice = c4.number_input("Price/Unit", value=float(ing['price_per_unit']), key=f"p_{i}_{v}", format="%.2f")

        # ROW CALCULATION
        row_total = round(iqty * iprice, 2)
        c5.write(f"**Total**\nरू {row_total}")

        # GET PRICE BUTTON
        if c6.button("🔍 Get Price", key=f"btn_{i}_{v}"):
            lookup = iname.strip().lower()
            if lookup in st.session_state.price_dict:
                # Update the source data AND bump the version to force-refresh the widget keys
                st.session_state.ingredients[i] = {
                    "item": iname,
                    "qty": iqty,
                    "unit": iunit,
                    "price_per_unit": st.session_state.price_dict[lookup],
                    "version": v + 1  # Bumping this forces Streamlit to re-render these specific widgets
                }
                st.rerun()
            else:
                st.error("Item Not Found")

        # Accumulate the state for current render
        updated_ingredients.append({
            "item": iname, "qty": iqty, "unit": iunit,
            "price_per_unit": iprice, "version": v, "total": row_total
        })

    st.session_state.ingredients = updated_ingredients

    if st.button("➕ Add New Ingredient Row"):
        st.session_state.ingredients.append({"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0, "version": 0})
        st.rerun()

    # --- 4. TOTALS & DATABASE ACTIONS ---
    st.divider()
    yld = st.number_input("Yield (Total pieces or cups produced)", value=st.session_state.current_yield, min_value=0.01)
    st.session_state.current_yield = yld

    total_recipe_cost = sum(x.get('total', 0) for x in st.session_state.ingredients)
    cost_per_unit = round(total_recipe_cost / yld, 2) if yld > 0 else 0
    st.metric("Raw Material Cost / Unit", f"रू {cost_per_unit}")

    col_save, col_del = st.columns(2)
    with col_save:
        if st.button("💾 Save to Master Records", type="primary", use_container_width=True):
            entry = {
                "Product Info": {"Name": prod_name, "Yield": yld, "Raw Mat/Unit": cost_per_unit,
                                 "MRP": round(cost_per_unit * 1.6, 2)},
                "Recipe": copy.deepcopy(st.session_state.ingredients)
            }
            # Add or Overwrite
            idx = next((index for index, r in enumerate(st.session_state.master_records) if
                        r["Product Info"]["Name"] == prod_name), None)
            if idx is not None:
                st.session_state.master_records[idx] = entry
            else:
                st.session_state.master_records.append(entry)
            st.success(f"'{prod_name}' has been saved/updated!")
            st.rerun()

    with col_del:
        if st.session_state.master_records:
            names = [r["Product Info"]["Name"] for r in st.session_state.master_records]
            to_del = st.selectbox("Select Item to Delete", ["-- Select --"] + names)
            if st.button("🗑️ Delete Selected Item", use_container_width=True) and to_del != "-- Select --":
                st.session_state.master_records = [r for r in st.session_state.master_records if
                                                   r["Product Info"]["Name"] != to_del]
                st.rerun()

    # --- 5. MASTER DATABASE ENLISTMENT ---
    if st.session_state.master_records:
        st.divider()
        st.subheader("📋 Master Recipe Database")
        final_table = []
        for r in st.session_state.master_records:
            inf = r["Product Info"]
            # Header Row for the Product
            final_table.append(
                {"Item": f"--- PRODUCT: {inf['Name']} ---", "Raw Mat/Unit": inf['Raw Mat/Unit'], "Yield": inf['Yield'],
                 "MRP": inf.get('MRP', 0)})
            # Rows for Ingredients
            for ig in r["Recipe"]:
                if ig["item"]:
                    final_table.append(
                        {"Item": ig["item"], "Qty": ig["qty"], "Unit": ig["unit"], "Price/Unit": ig["price_per_unit"],
                         "Total Cost": round(ig['qty'] * ig['price_per_unit'], 2)})

        df_master = pd.DataFrame(final_table).fillna("")
        st.dataframe(df_master.astype(str), use_container_width=True)

        # EXPORT TO EXCEL
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_master.to_excel(writer, index=False)
        st.download_button("📥 Download Full Master List (Excel)", data=output.getvalue(),
                           file_name="bakery_master_list.xlsx", use_container_width=True)


if __name__ == "__main__":
    ultimate_bakery_manager()