import streamlit as st
import pandas as pd
import json
import os
import uuid

# --- 1. DATA PERSISTENCE & VISUAL EXCEL SYNC ---
DATA_JSON = "bagels_persistence.json"


def save_all_to_disk():
    serializable_data = {
        "master_records": st.session_state.master_records,
        "price_dict": st.session_state.price_dict,
        "overheads": st.session_state.overheads,
        "target_excel": st.session_state.get("target_excel", "bagels_business_master.xlsx")
    }
    with open(DATA_JSON, "w") as f:
        json.dump(serializable_data, f)

    target = st.session_state.get("target_excel")
    if target:
        try:
            sync_to_excel(target)
        except Exception as e:
            st.error(f"❌ Excel Sync Failed: {e}")


def sync_to_excel(filename):
    """Generates a visually formatted Excel file with colors and borders."""
    rows = []
    product_row_indices = []

    for r in st.session_state.master_records:
        inf = r["Info"]
        product_row_indices.append(len(rows) + 1)

        rows.append({
            "Item": f"PRODUCT: {inf['Name']}", "Qty": "", "Unit": "", "Price/Unit": "",
            "Total Cost": inf.get('Total Cost', 0), "Raw Mat/Unit": inf.get('Raw Mat/Unit', 0),
            "Yield": inf.get('Yield', 1.0), "Waste %": inf.get('Waste %', 0),
            "MRP": inf.get('MRP', 0), "Margin %": inf.get('Margin %', 0),
            "OH Alloc %": inf.get('OH Alloc %', 100), "Pkg/Unit": inf.get('Pkg/Unit', 0)
        })
        for ig in r["Recipe"]:
            rows.append({
                "Item": ig['item'], "Qty": ig['qty'], "Unit": ig['unit'],
                "Price/Unit": ig['price_per_unit'],
                "Total Cost": round(float(ig['qty']) * float(ig['price_per_unit']), 2),
                "Raw Mat/Unit": "", "Yield": "", "Waste %": "", "MRP": "", "Margin %": "", "OH Alloc %": "",
                "Pkg/Unit": ""
            })

    df = pd.DataFrame(rows)
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Master Data')

    workbook = writer.book
    worksheet = writer.sheets['Master Data']

    header_fmt = workbook.add_format({'bold': True, 'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
    prod_fmt = workbook.add_format({'bold': True, 'fg_color': '#DDEBF7', 'border': 1})
    border_fmt = workbook.add_format({'border': 1})

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_fmt)

    for row_num in range(len(rows)):
        fmt = prod_fmt if (row_num + 1) in product_row_indices else border_fmt
        for col_num in range(len(df.columns)):
            val = df.iloc[row_num, col_num]
            worksheet.write(row_num + 1, col_num, val, fmt)

    worksheet.set_column('A:A', 30)
    worksheet.set_column('B:L', 12)
    writer.close()


def load_persistence():
    if os.path.exists(DATA_JSON):
        try:
            with open(DATA_JSON, "r") as f:
                data = json.load(f)
                st.session_state.master_records = data.get("master_records", [])
                st.session_state.price_dict = data.get("price_dict", {})
                st.session_state.overheads = data.get("overheads", {
                    "rent": 150000.0, "salaries": 150000.0, "utilities": 50000.0,
                    "marketing": 10000.0, "assets": 2000000.0, "dep_years": 5, "monthly_units": 2000
                })
                st.session_state.target_excel = data.get("target_excel", "bagels_business_master.xlsx")
                return True
        except:
            return False
    return False


def rd(v):
    try:
        return round(float(v), 2)
    except:
        return 0.0


def add_row():
    st.session_state.recipe_buffer.append(
        {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0})


def delete_row(row_id):
    st.session_state.recipe_buffer = [r for r in st.session_state.recipe_buffer if r["id"] != row_id]


# --- 3. MAIN APP ---
def bagels_co_master_engine():
    st.set_page_config(page_title="Bagels & Co. | Master Business Engine", layout="wide")

    if 'initialized' not in st.session_state:
        if not load_persistence():
            st.session_state.master_records = []
            st.session_state.price_dict = {}
            st.session_state.overheads = {"rent": 150000.0, "salaries": 150000.0, "utilities": 50000.0,
                                          "marketing": 10000.0, "assets": 2000000.0, "dep_years": 5,
                                          "monthly_units": 2000}
        st.session_state.editing_name = "New Item"
        st.session_state.load_id = 0
        st.session_state.recipe_buffer = [
            {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
        st.session_state.current_strategy = {"Yield": 1.0, "Waste %": 5.0, "Pkg/Unit": 15.0, "OH Alloc %": 100,
                                             "Margin %": 50.0, "VAT On": True}
        st.session_state.confirm_delete = False
        st.session_state.initialized = True

    # --- SIDEBAR & TOP NAV (Unchanged logic) ---
    st.sidebar.header("📁 Data Management")
    p_file = st.sidebar.file_uploader("1. Sync Market Prices", type=["xlsx", "csv"])
    if p_file and st.sidebar.button("🔄 Update Market Prices"):
        df_p = pd.read_excel(p_file) if p_file.name.endswith('.xlsx') else pd.read_csv(p_file)
        if "Ingredient Name" not in df_p.columns:
            for i in range(5):
                if "Ingredient Name" in df_p.iloc[i].values:
                    df_p.columns = df_p.iloc[i];
                    df_p = df_p[i + 1:];
                    break
        st.session_state.price_dict = {
            str(row.get('Ingredient Name', '')).strip().lower(): rd(row.get('Price per Unit', 0)) for _, row in
            df_p.iterrows()}
        save_all_to_disk();
        st.rerun()

    db_file = st.sidebar.file_uploader("2. Link Master Excel", type=["xlsx"])
    if db_file and st.sidebar.button("🔗 Restore Database"):
        df_res = pd.read_excel(db_file).fillna("")
        temp_recs, curr_prod = [], None
        for _, row in df_res.iterrows():
            item_str = str(row.get('Item', '')).strip()
            if "PRODUCT:" in item_str:
                curr_prod = {"Info": {"Name": item_str.replace("PRODUCT:", "").strip(),
                                      "Raw Mat/Unit": rd(row.get('Raw Mat/Unit', 0)),
                                      "Yield": rd(row.get('Yield', 1.0)),
                                      "Waste %": rd(row.get('Waste %', 0)), "MRP": rd(row.get('MRP', 0)),
                                      "Margin %": rd(row.get('Margin %', 0)),
                                      "OH Alloc %": rd(row.get('OH Alloc %', 100)),
                                      "Pkg/Unit": rd(row.get('Pkg/Unit', 0)),
                                      "Total Cost": rd(row.get('Total Cost', 0)), "VAT On": True}, "Recipe": []}
                temp_recs.append(curr_prod)
            elif curr_prod and item_str and not item_str.startswith("---"):
                curr_prod["Recipe"].append(
                    {"item": item_str, "qty": rd(row.get('Qty', 0)), "unit": str(row.get('Unit', 'g')),
                     "price_per_unit": rd(row.get('Price/Unit', 0))})
        st.session_state.master_records = temp_recs;
        save_all_to_disk();
        st.rerun()

    st.title("🥯 Bagels & Co. | Master Business Engine")
    n1, n2, n3 = st.columns([2, 1, 1])
    with n1:
        names = sorted(list(set(r["Info"]["Name"] for r in st.session_state.master_records)))
        sel = st.selectbox("📂 Load Existing Product", ["-- Select --"] + names)
        if st.button("📂 Open Product") and sel != "-- Select --":
            rec = next(r for r in st.session_state.master_records if r["Info"]["Name"] == sel)
            st.session_state.recipe_buffer = [
                {"id": str(uuid.uuid4()), "item": i['item'], "qty": i['qty'], "unit": i['unit'],
                 "price": i['price_per_unit'], "v": 0} for i in rec["Recipe"]]
            st.session_state.current_strategy = rec["Info"];
            st.session_state.editing_name = rec["Info"]["Name"];
            st.session_state.load_id += 1;
            st.rerun()
    with n2:
        st.write("---")
        if st.button("➕ New Product", use_container_width=True):
            st.session_state.recipe_buffer = [
                {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
            st.session_state.current_strategy = {"Yield": 1.0, "Waste %": 5.0, "Pkg/Unit": 15.0, "OH Alloc %": 100,
                                                 "Margin %": 50.0, "VAT On": True}
            st.session_state.editing_name = "New Item";
            st.session_state.load_id += 1;
            st.rerun()
    with n3:
        st.write("---")
        if not st.session_state.confirm_delete:
            if st.button("🗑️ Delete Product Entry",
                         use_container_width=True): st.session_state.confirm_delete = True; st.rerun()
        else:
            st.warning(f"Delete {st.session_state.editing_name}?");
            c1, c2 = st.columns(2)
            if c1.button("✅ Yes", type="primary"):
                st.session_state.master_records = [r for r in st.session_state.master_records if
                                                   r["Info"]["Name"] != st.session_state.editing_name]
                save_all_to_disk();
                st.session_state.confirm_delete = False;
                st.rerun()
            if c2.button("❌ No"): st.session_state.confirm_delete = False; st.rerun()

    # --- 4. OVERHEADS & RECIPE (Unchanged logic) ---
    with st.expander("🏢 Monthly Overheads & Depreciation"):
        o = st.session_state.overheads
        c1, c2, c3 = st.columns(3)
        o["rent"] = c1.number_input("Monthly Rent", value=o["rent"]);
        o["salaries"] = c2.number_input("Staff Salaries", value=o["salaries"]);
        o["utilities"] = c3.number_input("Utilities", value=o["utilities"])
        o["marketing"] = st.number_input("Marketing Cost", value=o["marketing"]);
        o["assets"] = st.number_input("Kitchen Asset Value", value=o["assets"]);
        o["monthly_units"] = st.number_input("Expected Units/Month", value=o["monthly_units"])
        o["dep_years"] = st.slider("Depreciation Period (Years)", 1, 15, o["dep_years"])
        avg_oh_per_unit = rd(
            (o["rent"] + o["salaries"] + o["utilities"] + o["marketing"] + rd(o["assets"] / (o["dep_years"] * 12))) / o[
                "monthly_units"])
        st.info(f"**Allocated OH/Unit (100%):** रू {avg_oh_per_unit}")

    st.subheader("🥣 Recipe Construction")
    lid = st.session_state.load_id;
    p_name = st.text_input("Product Name", value=st.session_state.editing_name, key=f"pn_{lid}")
    market_items = sorted([k.title() for k in st.session_state.price_dict.keys()])
    updated_buffer = []
    for i, row in enumerate(st.session_state.recipe_buffer):
        uid = row["id"];
        cols = st.columns([3, 1, 1, 1.5, 1.5, 0.5])
        cur_val = row['item'].title();
        opts = [""] + market_items
        if cur_val and cur_val not in opts: opts.append(cur_val)
        sel_item = cols[0].selectbox(f"Ingredient {i + 1}", opts, index=opts.index(cur_val) if cur_val in opts else 0,
                                     key=f"s_{uid}_{lid}")
        if sel_item.lower() != row['item']:
            row['item'] = sel_item.lower();
            row['price'] = st.session_state.price_dict.get(sel_item.lower(), 0.0);
            row['v'] += 1;
            st.rerun()
        qty = cols[1].number_input("Qty", 0.0, value=float(row['qty']), key=f"q_{uid}_{lid}")
        unit = cols[2].selectbox("Unit", ["g", "kg", "ml", "ltr", "pcs"], key=f"u_{uid}_{lid}",
                                 index=["g", "kg", "ml", "ltr", "pcs"].index(row['unit']))
        price = cols[3].number_input("Price/Unit", 0.0, value=float(row['price']), key=f"p_{uid}_{row['v']}_{lid}")
        row_tot = rd(qty * price);
        cols[4].markdown(f"**रू {row_tot}**")
        if cols[5].button("🗑️", key=f"del_{uid}_{lid}"): delete_row(uid); st.rerun()
        updated_buffer.append(
            {"id": uid, "item": sel_item.lower(), "qty": qty, "unit": unit, "price": price, "total": row_tot,
             "v": row['v']})
    st.session_state.recipe_buffer = updated_buffer
    if st.button("➕ Add Ingredient Row"): add_row(); st.rerun()

    # --- 5. STRATEGY & SUMMARY ---
    st.divider();
    strat = st.session_state.current_strategy;
    f1, f2, f3, f4 = st.columns(4)
    yld = f1.number_input("Yield (Units)", 0.01, value=float(strat.get("Yield", 1.0)), key=f"yld_{lid}")
    wst = f2.number_input("Waste %", 0.0, value=float(strat.get("Waste %", 5.0)), key=f"wst_{lid}")
    pkg = f3.number_input("Pkg/Unit", 0.0, value=float(strat.get("Pkg/Unit", 15.0)), key=f"pkg_{lid}")
    marg = f4.number_input("Margin %", 0.0, value=float(strat.get("Margin %", 50.0)), key=f"mr_{lid}")
    o_alloc = st.slider("OH Allocation %", 0, 200, value=int(strat.get("OH Alloc %", 100)), key=f"o_{lid}")
    vat = st.checkbox("Apply 13% VAT", value=strat.get("VAT On", True), key=f"v_{lid}")

    unit_raw = rd((sum(r['total'] for r in st.session_state.recipe_buffer) / (1 - (wst / 100))) / yld)
    unit_oh = rd(avg_oh_per_unit * (o_alloc / 100))
    final_cost = rd(unit_raw + unit_oh + pkg);
    net_price = rd(final_cost / (1 - (marg / 100))) if marg < 100 else final_cost
    mrp = rd(net_price * 1.13) if vat else net_price

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Raw Mat/Unit", f"रू {unit_raw}");
    c2.metric("OH/Unit", f"रू {unit_oh}");
    c3.metric("Net Price", f"रू {net_price}");
    c4.metric("VAT (13%)", f"रू {rd(mrp - net_price)}");
    c5.metric("Final MRP", f"रू {mrp}")

    if st.button("💾 SAVE & SYNC TO EXCEL", type="primary", use_container_width=True):
        info = {"Name": p_name, "Yield": yld, "Waste %": wst, "Pkg/Unit": pkg, "Margin %": marg, "OH Alloc %": o_alloc,
                "VAT On": vat, "MRP": mrp, "Total Cost": sum(r['total'] for r in st.session_state.recipe_buffer),
                "Raw Mat/Unit": unit_raw}
        rec_data = [{"item": i['item'], "qty": i['qty'], "unit": i['unit'], "price_per_unit": i['price']} for i in
                    st.session_state.recipe_buffer if i['item'] != ""]
        idx = next((i for i, r in enumerate(st.session_state.master_records) if r["Info"]["Name"] == p_name), None)
        if idx is not None:
            st.session_state.master_records[idx] = {"Info": info, "Recipe": rec_data}
        else:
            st.session_state.master_records.append({"Info": info, "Recipe": rec_data})
        save_all_to_disk();
        st.success(f"✅ {p_name} Saved & Formatted!")

    # --- 6. MASTER REVIEW (RESTORED FULL COLUMNS) ---
    if st.session_state.master_records:
        st.divider();
        st.subheader("📋 Master Review (Full Data Mirror)")
        rev_rows = []
        for r in st.session_state.master_records:
            inf = r["Info"]
            rev_rows.append({
                "Item": f"PRODUCT: {inf['Name']}", "Qty": "", "Unit": "", "Price/Unit": "",
                "Total Cost": str(inf.get('Total Cost', 0)), "Raw Mat/Unit": str(inf.get('Raw Mat/Unit', 0)),
                "Yield": str(inf.get('Yield', 1.0)), "Waste %": str(inf.get('Waste %', 0)),
                "MRP": str(inf.get('MRP', 0)), "Margin %": str(inf.get('Margin %', 0)),
                "OH Alloc %": str(inf.get('OH Alloc %', 100)), "Pkg/Unit": str(inf.get('Pkg/Unit', 0))
            })
            for ig in r["Recipe"]:
                rev_rows.append({
                    "Item": ig['item'], "Qty": str(ig['qty']), "Unit": ig['unit'],
                    "Price/Unit": str(ig['price_per_unit']), "Total Cost": str(rd(ig['qty'] * ig['price_per_unit'])),
                    "Raw Mat/Unit": "", "Yield": "", "Waste %": "", "MRP": "", "Margin %": "", "OH Alloc %": "",
                    "Pkg/Unit": ""
                })
        st.dataframe(pd.DataFrame(rev_rows).astype(str), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    bagels_co_master_engine()