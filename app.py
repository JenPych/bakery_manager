import streamlit as st
import pandas as pd
from io import BytesIO
import copy

try:
    import xlsxwriter
except ImportError:
    st.error("Please install xlsxwriter: pip install xlsxwriter")


def ultimate_bakery_manager():
    st.set_page_config(page_title="Bakery Master Pro", layout="wide")
    st.title("🇳🇵 Bakery Master: Unit-Based Pricing & Recipe Manager")

    # --- 1. SESSION STATE ---
    if 'master_records' not in st.session_state:
        st.session_state.master_records = []
    if 'ingredients' not in st.session_state:
        st.session_state.ingredients = [{"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0}]
    if 'current_yield' not in st.session_state:
        st.session_state.current_yield = 1.0
    if 'recipe_version' not in st.session_state:
        st.session_state.recipe_version = 0

    # --- 2. SIDEBAR: OVERHEADS ---
    st.sidebar.header("🏢 Monthly Fixed Overheads")
    rent = st.sidebar.number_input("Monthly Rent (रू)", value=45000)
    salaries = st.sidebar.number_input("Staff Salaries (रू)", value=90000)
    utilities = st.sidebar.number_input("Utility Bills (रू)", value=8000)
    asset_val = st.sidebar.number_input("Equipment Value (रू)", value=500000)
    lifespan = st.sidebar.slider("Lifespan (Years)", 1, 15, 5)

    monthly_dep = (asset_val / lifespan) / 12 if lifespan > 0 else 0
    total_fixed_monthly = rent + salaries + utilities + monthly_dep
    target_volume = st.sidebar.number_input("Total Monthly Units (Total Pieces Sold)", value=2000, min_value=1)
    fixed_share_per_unit = total_fixed_monthly / target_volume

    # --- 3. DATA IMPORT ---
    st.sidebar.header("📂 Data Continuity")
    uploaded_file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded_file is not None and st.sidebar.button("Import Data"):
        try:
            df_import = pd.read_excel(uploaded_file).fillna("")
            temp_records = []
            current_product = None

            def safe_float(x):
                try:
                    return float(x) if str(x).strip() != "" else 0.0
                except:
                    return 0.0

            for _, row in df_import.iterrows():
                val = str(row['Product/Ingredient']).strip()
                if not val: continue

                if "--- PRODUCT:" in val:
                    name = val.replace("--- PRODUCT: ", "").replace(" ---", "")
                    current_product = {
                        "Product Info": {
                            "Name": name,
                            "Yield": safe_float(row.get('Yield', 1.0)),
                            "Raw Mat/Unit": safe_float(row.get('Raw Mat/Unit', 0.0)),
                            "Full Batch MRP": safe_float(row.get('Full Batch MRP', 0.0)),
                            "Per Piece MRP": safe_float(row.get('Per Piece MRP', 0.0)),
                            "Delivery MRP": safe_float(row.get('Delivery MRP', 0.0))
                        },
                        "Recipe": []
                    }
                    temp_records.append(current_product)
                elif current_product and not val.startswith("---"):
                    current_product["Recipe"].append({
                        "item": val, "qty": safe_float(row.get('Qty', 0.0)),
                        "unit": str(row.get('Unit', 'g')),
                        "price_per_unit": safe_float(row.get('Price/Unit', 0.0)),
                        "total": safe_float(row.get('Total Cost', 0.0))
                    })
            st.session_state.master_records = temp_records
            st.sidebar.success(f"Imported {len(temp_records)} Products")
        except Exception as e:
            st.sidebar.error(f"Import Error: {e}")

    # --- 4. RECIPE EDITOR ---
    st.header("🥣 Recipe Editor")
    existing_names = [r["Product Info"]["Name"] for r in st.session_state.master_records]
    col_name, col_status = st.columns([2, 1])
    product_name = col_name.text_input("Product Name", value="New Product")

    if product_name in existing_names:
        col_status.info("🔄 Product Loaded")
        if st.button("Refresh Fields"):
            match = next(
                item for item in st.session_state.master_records if item["Product Info"]["Name"] == product_name)
            st.session_state.ingredients = copy.deepcopy(match["Recipe"])
            st.session_state.current_yield = float(match["Product Info"]["Yield"])
            st.session_state.recipe_version += 1
            st.rerun()

    v = st.session_state.recipe_version
    updated_ingredients = []
    for i, ing in enumerate(st.session_state.ingredients):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 2, 1])
        i_name = c1.text_input("Ingredient Name", value=ing["item"], key=f"n_{v}_{i}")
        i_qty = c2.number_input("Qty Used", value=float(ing["qty"]), key=f"q_{v}_{i}", format="%.2f")
        i_unit = c3.selectbox("Unit", ["g", "kg", "ml", "ltr", "pcs"],
                              index=["g", "kg", "ml", "ltr", "pcs"].index(ing["unit"]), key=f"u_{v}_{i}")
        i_price = c4.number_input("Price/Unit", value=float(ing["price_per_unit"]), key=f"p_{v}_{i}", format="%.2f")
        i_total = i_qty * i_price
        c5.write(f"**Total**\nरू {i_total:.2f}")
        updated_ingredients.append(
            {"item": i_name, "qty": i_qty, "unit": i_unit, "price_per_unit": i_price, "total": i_total})

    st.session_state.ingredients = updated_ingredients

    btn1, btn2 = st.columns([1, 5])
    if btn1.button("➕ Add Row"):
        st.session_state.ingredients.append({"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0})
        st.rerun()
    if btn2.button("🗑️ Reset Form"):
        st.session_state.ingredients = [{"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0}]
        st.session_state.current_yield = 1.0
        st.session_state.recipe_version += 1
        st.rerun()

    # --- 5. CALCULATIONS (PIECE-BASED) ---
    st.divider()
    total_recipe_cost = sum(ing["total"] for ing in st.session_state.ingredients)

    # CLEARLY LABELLED AS PIECES
    yield_qty = st.number_input("Yield (Total pieces produced from this recipe)", value=st.session_state.current_yield,
                                min_value=0.01, key=f"y_{v}")
    st.session_state.current_yield = yield_qty

    ca, cb = st.columns(2)
    with ca:
        loss_pct = st.number_input("Wastage & Buffer %", value=12.0)
        pack_cost = st.number_input("Packaging Cost/piece", value=15.0)

        raw_mat_per_unit = total_recipe_cost / yield_qty if yield_qty > 0 else 0
        cost_with_wastage = raw_mat_per_unit * (1 + (loss_pct / 100))
        final_cost_absorbed = cost_with_wastage + pack_cost + fixed_share_per_unit

    with cb:
        margin = st.slider("Target Margin %", 10, 200, 40)
        base_piece = final_cost_absorbed * (1 + (margin / 100))
        mrp_per_piece = round((base_piece * 1.13) / 5) * 5
        mrp_full_batch = mrp_per_piece * yield_qty
        mrp_delivery = round(((base_piece / 0.8) * 1.13) / 5) * 5
        st.metric("Per Piece MRP", f"रू {mrp_per_piece:.2f}")
        st.success(f"**Full Batch MRP: रू {mrp_full_batch:.2f}**")

    # --- 6. SAVE & DELETE ---
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("💾 Save Product", use_container_width=True):
            new_entry = {
                "Product Info": {
                    "Name": product_name, "Yield": yield_qty, "Raw Mat/Unit": round(raw_mat_per_unit, 2),
                    "Full Batch MRP": mrp_full_batch, "Per Piece MRP": mrp_per_piece, "Delivery MRP": mrp_delivery
                },
                "Recipe": copy.deepcopy(st.session_state.ingredients)
            }
            idx = next(
                (i for i, r in enumerate(st.session_state.master_records) if r["Product Info"]["Name"] == product_name),
                None)
            if idx is not None:
                st.session_state.master_records[idx] = new_entry
            else:
                st.session_state.master_records.append(new_entry)
            st.success(f"'{product_name}' Saved!")
            st.rerun()

    with sc2:
        if st.session_state.master_records:
            to_delete = st.selectbox("Select Product to Remove", options=["-- Select --"] + existing_names)
            if st.button("🗑️ Delete Selected Product", type="secondary", use_container_width=True):
                if to_delete != "-- Select --":
                    st.session_state.master_records = [r for r in st.session_state.master_records if
                                                       r["Product Info"]["Name"] != to_delete]
                    st.warning(f"'{to_delete}' removed.")
                    st.rerun()

    # --- 7. MASTER LIST ---
    if st.session_state.master_records:
        st.divider()
        st.subheader("📋 Master Database")
        export_rows = []
        cols_order = ["Product/Ingredient", "Qty", "Unit", "Price/Unit", "Total Cost", "Raw Mat/Unit", "Yield",
                      "Full Batch MRP", "Per Piece MRP", "Delivery MRP"]

        for rec in st.session_state.master_records:
            info = rec["Product Info"]
            export_rows.append({
                "Product/Ingredient": f"--- PRODUCT: {info['Name']} ---",
                "Raw Mat/Unit": info['Raw Mat/Unit'], "Yield": info['Yield'],
                "Full Batch MRP": info['Full Batch MRP'], "Per Piece MRP": info['Per Piece MRP'],
                "Delivery MRP": info['Delivery MRP']
            })
            for ing in rec["Recipe"]:
                if ing["item"]:
                    export_rows.append({"Product/Ingredient": ing["item"], "Qty": ing["qty"], "Unit": ing['unit'],
                                        "Price/Unit": ing['price_per_unit'], "Total Cost": ing['total']})
            export_rows.append({c: "" for c in cols_order})

        df_final = pd.DataFrame(export_rows).reindex(columns=cols_order).fillna("")
        st.dataframe(df_final.astype(str), width='stretch')

        out = BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False)
        st.download_button("📥 Download Master Excel", data=out.getvalue(), file_name="bakery_database.xlsx")


if __name__ == "__main__":
    ultimate_bakery_manager()