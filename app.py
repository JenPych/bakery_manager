import streamlit as st
import pandas as pd
from io import BytesIO

# Ensure xlsxwriter is available
try:
    import xlsxwriter
except ImportError:
    st.error("Please install xlsxwriter: pip install xlsxwriter")


def ultimate_bakery_manager():
    st.set_page_config(page_title="Bakery Recipe Manager", layout="wide")
    st.title("🇳🇵 Professional Recipe Manager & Data Updater")

    # --- SESSION STATE ---
    if 'master_records' not in st.session_state:
        st.session_state.master_records = []

    if 'ingredients' not in st.session_state:
        st.session_state.ingredients = [{"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0}]

    # --- SIDEBAR: OVERHEADS ---
    st.sidebar.header("🏢 Monthly Fixed Overheads")
    rent = st.sidebar.number_input("Monthly Rent (रू)", value=45000)
    salaries = st.sidebar.number_input("Staff Salaries (रू)", value=90000)
    utilities = st.sidebar.number_input("Utility Bills (रू)", value=8000)

    asset_val = st.sidebar.number_input("Equipment Value (रू)", value=500000)
    lifespan = st.sidebar.slider("Lifespan (Years)", 1, 15, 5)
    monthly_dep = (asset_val / lifespan) / 12
    total_fixed_monthly = rent + salaries + utilities + monthly_dep

    st.sidebar.divider()
    target_volume = st.sidebar.number_input("Total Monthly Units (All Items)", value=2000, min_value=1)
    fixed_share_per_unit = total_fixed_monthly / target_volume

    # --- NEW: UPLOAD EXISTING FILE ---
    st.sidebar.header("📂 Data Continuity")
    uploaded_file = st.sidebar.file_uploader("Upload 'bakery_recipe_book.xlsx' to continue", type=["xlsx"])

    if uploaded_file is not None and st.sidebar.button("Import Data from File"):
        try:
            df_import = pd.read_excel(uploaded_file)
            # Logic to reconstruct master_records from the flat Excel structure
            temp_records = []
            current_product = None

            for _, row in df_import.iterrows():
                val = str(row['Product/Ingredient'])
                if "--- PRODUCT:" in val:
                    name = val.replace("--- PRODUCT: ", "").replace(" ---", "")
                    current_product = {
                        "Product Info": {
                            "Name": name,
                            "Yield": row['Yield'],
                            "Raw Mat/Unit": row['Raw Mat/Unit'],
                            "Dine-In MRP": row['Dine-In MRP'],
                            "Delivery MRP": row['Delivery MRP']
                        },
                        "Recipe": []
                    }
                    temp_records.append(current_product)
                elif val and val != "nan" and current_product:
                    current_product["Recipe"].append({
                        "item": val,
                        "qty": row['Qty'],
                        "unit": row['Unit'],
                        "price_per_unit": row['Price/Unit'],
                        "total": row['Total Cost']
                    })
            st.session_state.master_records = temp_records
            st.sidebar.success("Successfully imported saved products!")
        except Exception as e:
            st.sidebar.error("Error: Make sure the file matches the exported format.")

    # --- MAIN SECTION: RECIPE BUILDER ---
    st.header("🥣 Recipe Builder")
    product_name = st.text_input("Product Name", value="New Product")

    new_ingredients = []
    for i, ing in enumerate(st.session_state.ingredients):
        cols = st.columns([3, 1, 1, 2, 1])
        name = cols[0].text_input(f"Ingredient", value=ing["item"], key=f"name_{i}")
        qty = cols[1].number_input("Qty", value=ing["qty"], key=f"qty_{i}", format="%.2f")
        unit = cols[2].selectbox("Unit", ["g", "kg", "ml", "ltr", "pcs"],
                                 index=["g", "kg", "ml", "ltr", "pcs"].index(ing["unit"]), key=f"unit_{i}")
        price = cols[3].number_input("Price/Unit (रू)", value=ing["price_per_unit"], key=f"price_{i}", format="%.2f")

        row_total = qty * price
        cols[4].write(f"**Total**\nरू {row_total:.2f}")
        new_ingredients.append({"item": name, "qty": qty, "unit": unit, "price_per_unit": price, "total": row_total})

    st.session_state.ingredients = new_ingredients

    c1, c2 = st.columns([1, 4])
    if c1.button("➕ Add Row"):
        st.session_state.ingredients.append({"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0})
        st.rerun()
    if c2.button("🗑️ Clear Form"):
        st.session_state.ingredients = [{"item": "", "qty": 0.0, "unit": "g", "price_per_unit": 0.0}]
        st.rerun()

    # --- PRICING ---
    st.divider()
    total_recipe_cost = sum(ing["total"] for ing in st.session_state.ingredients)
    yield_qty = st.number_input("Yield per Recipe", value=10, min_value=1)
    raw_mat_unit = total_recipe_cost / yield_qty

    col_a, col_b = st.columns(2)
    with col_a:
        spoilage_pct = st.number_input("Wastage %", value=7.0)
        buffer_pct = st.number_input("Buffer %", value=5.0)
        packaging = st.number_input("Packaging (रू)", value=15.0)
        total_var_unit = raw_mat_unit + (raw_mat_unit * (spoilage_pct + buffer_pct) / 100) + packaging
        total_cost_absorbed = total_var_unit + fixed_share_per_unit

    with col_b:
        margin_pct = st.slider("Net Margin %", 10, 200, 40)
        base_dine = total_cost_absorbed * (1 + margin_pct / 100)
        mrp_dine = base_dine * 1.13
        mrp_delivery = (base_dine / 0.8) * 1.13
        st.success(f"Dine-In MRP: रू {mrp_dine:.2f} | Delivery MRP: रू {mrp_delivery:.2f}")

    if st.button("💾 Save Product to Master List"):
        st.session_state.master_records.append({
            "Product Info": {"Name": product_name, "Yield": yield_qty, "Raw Mat/Unit": round(raw_mat_unit, 2),
                             "Dine-In MRP": round(mrp_dine, 2), "Delivery MRP": round(mrp_delivery, 2)},
            "Recipe": st.session_state.ingredients
        })
        st.toast("Product Saved!")

    # --- MASTER RECORDS & CONFIRMED RESET ---
    if st.session_state.master_records:
        st.divider()
        st.subheader("📋 Master List & Export")

        # Reset Confirmation Logic
        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            if st.button("❌ Reset All Records"):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("Are you sure? This will wipe all unsaved changes in the current list.")
            cr1, cr2 = st.columns(2)
            if cr1.button("YES, I'm Sure"):
                st.session_state.master_records = []
                st.session_state.confirm_reset = False
                st.rerun()
            if cr2.button("NO, Cancel"):
                st.session_state.confirm_reset = False
                st.rerun()

        # Build Export Data
        export_data = []
        for record in st.session_state.master_records:
            info = record['Product Info']
            export_data.append({"Product/Ingredient": f"--- PRODUCT: {info['Name']} ---", "Yield": info['Yield'],
                                "Raw Mat/Unit": info['Raw Mat/Unit'], "Dine-In MRP": info['Dine-In MRP'],
                                "Delivery MRP": info['Delivery MRP']})
            for ing in record['Recipe']:
                if ing['item']:
                    export_data.append({"Product/Ingredient": ing['item'], "Qty": ing['qty'], "Unit": ing['unit'],
                                        "Price/Unit": ing['price_per_unit'], "Total Cost": ing['total']})
            export_data.append({k: "" for k in ["Product/Ingredient"]})

        df_export = pd.DataFrame(export_data)
        st.dataframe(df_export)

        # Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Recipes')

        st.download_button("📥 Download Excel Sheet", data=output.getvalue(), file_name="bakery_recipe_book.xlsx")


if __name__ == "__main__":
    ultimate_bakery_manager()