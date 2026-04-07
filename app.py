import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid

# --- 1. DATA PERSISTENCE & CLOUD SYNC ---
conn = st.connection("gsheets", type=GSheetsConnection)


def rd(v):
    """Safe rounding for financial display."""
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0


def load_market_prices():
    try:
        df_p = conn.read(worksheet="Market Prices", ttl=0)
        if df_p is None or df_p.empty: return {}
        # Standardizing column names to avoid case sensitivity issues
        df_p.columns = [c.strip() for c in df_p.columns]
        NAME_COL, PRICE_COL = "Ingredient Name", "Price per Unit"

        if NAME_COL not in df_p.columns or PRICE_COL not in df_p.columns:
            st.sidebar.error(f"Headers mismatch! Expected: '{NAME_COL}' and '{PRICE_COL}'")
            return {}

        return {str(row[NAME_COL]).strip().lower(): rd(row[PRICE_COL])
                for _, row in df_p.iterrows() if pd.notnull(row[NAME_COL])}
    except Exception as e:
        st.sidebar.error(f"Price Load Error: {e}")
        return {}


def save_all_to_sheets():
    rows = []
    for r in st.session_state.master_records:
        inf = r["Info"]
        # Header Row for the Product
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
                "Price/Unit": ig['price_per_unit'], "Total Cost": rd(ig['qty'] * ig['price_per_unit']),
                "Raw Mat/Unit": 0, "Yield": 0, "Waste %": 0, "MRP": 0, "Margin %": 0, "OH Alloc %": 0, "Pkg/Unit": 0
            })
    try:
        conn.update(worksheet="Master Data", data=pd.DataFrame(rows))
        return True
    except Exception as e:
        st.error(f"Cloud Save Failed: {e}")
        return False


def load_persistence():
    try:
        df = conn.read(worksheet="Master Data", ttl=0)
        if df is None or df.empty: return False
        temp_recs, curr_prod = [], None

        for _, row in df.iterrows():
            item_str = str(row.get('Item', '')).strip()
            if item_str.startswith("PRODUCT:"):
                curr_prod = {
                    "Info": {
                        "Name": item_str.replace("PRODUCT:", "").strip(),
                        "Raw Mat/Unit": rd(row.get('Raw Mat/Unit', 0)),
                        "Yield": rd(row.get('Yield', 1.0)),
                        "Waste %": rd(row.get('Waste %', 0)),
                        "MRP": rd(row.get('MRP', 0)),
                        "Margin %": rd(row.get('Margin %', 0)),
                        "OH Alloc %": rd(row.get('OH Alloc %', 100)),
                        "Pkg/Unit": rd(row.get('Pkg/Unit', 0)),
                        "Total Cost": rd(row.get('Total Cost', 0)),
                        "VAT On": True
                    },
                    "Recipe": []
                }
                temp_recs.append(curr_prod)
            elif curr_prod and item_str:
                curr_prod["Recipe"].append({
                    "item": item_str,
                    "qty": rd(row.get('Qty', 0)),
                    "unit": str(row.get('Unit', 'g')),
                    "price_per_unit": rd(row.get('Price/Unit', 0))
                })
        st.session_state.master_records = temp_recs
        return True
    except:
        return False


def bagels_co_master_engine():
    st.set_page_config(page_title="Bagels & Co. | Master Business Engine", layout="wide")

    if 'initialized' not in st.session_state:
        st.session_state.master_records = []
        load_persistence()
        st.session_state.price_dict = load_market_prices()
        st.session_state.overheads = {
            "rent": 150000.0, "salaries": 150000.0, "utilities": 50000.0,
            "assets": 2000000.0, "dep_years": 5, "monthly_units": 2000
        }
        st.session_state.editing_name = "New Item"
        st.session_state.load_id = 0
        st.session_state.recipe_buffer = [
            {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
        st.session_state.current_strategy = {"Yield": 1.0, "Waste %": 5.0, "Pkg/Unit": 15.0, "OH Alloc %": 100,
                                             "Margin %": 50.0, "VAT On": True}
        st.session_state.save_success = False
        st.session_state.initialized = True

    st.title("🥯 Bagels & Co. | Cloud Master Engine")

    # --- NAV BAR ---
    n1, n2, n3 = st.columns([2, 0.8, 1.2])

    with n1:
        names = sorted(list(set(r["Info"]["Name"] for r in st.session_state.master_records)))
        sel = st.selectbox("📂 Load Product", ["-- Select --"] + names, label_visibility="collapsed")

    with n2:
        if st.button("📂 Open", use_container_width=True) and sel != "-- Select --":
            rec = next(r for r in st.session_state.master_records if r["Info"]["Name"] == sel)
            st.session_state.recipe_buffer = [
                {"id": str(uuid.uuid4()), "item": i['item'], "qty": i['qty'], "unit": i['unit'],
                 "price": i['price_per_unit'], "v": 0} for i in rec["Recipe"]]
            st.session_state.current_strategy, st.session_state.editing_name = rec["Info"], rec["Info"]["Name"]
            st.session_state.load_id += 1
            st.session_state.save_success = False
            st.rerun()

    with n3:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            if st.button("➕ New", use_container_width=True):
                st.session_state.recipe_buffer = [
                    {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
                st.session_state.editing_name, st.session_state.load_id = "New Item", st.session_state.load_id + 1
                st.session_state.save_success = False
                st.rerun()

        with sub_c2:
            # --- DELETE WITH CONFIRMATION POPUP ---
            if sel != "-- Select --":
                with st.popover("🗑️ Delete", use_container_width=True):
                    st.warning(f"Confirm deletion of '{sel}'?")
                    if st.button("Yes, Delete permanently", type="primary"):
                        # 1. Remove from local session state
                        st.session_state.master_records = [r for r in st.session_state.master_records if
                                                           r["Info"]["Name"] != sel]

                        # 2. Sync the shortened list back to Google Sheets
                        if save_all_to_sheets():
                            st.toast(f"Deleted {sel} from Cloud")
                            # Reset UI to a clean state
                            st.session_state.recipe_buffer = [
                                {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0}]
                            st.session_state.editing_name = "New Item"
                            st.session_state.load_id += 1
                            st.rerun()
            else:
                st.button("🗑️", disabled=True, use_container_width=True)

    # --- OVERHEADS ---
    with st.expander("🏢 Monthly Overheads & Depreciation"):
        o = st.session_state.overheads
        c1, c2, c3 = st.columns(3)
        o["rent"] = c1.number_input("Monthly Rent", value=o["rent"], step=500.0)
        o["salaries"] = c2.number_input("Staff Salaries", value=o["salaries"], step=500.0)
        o["utilities"] = c3.number_input("Utilities", value=o["utilities"], step=100.0)

        c4, c5, c6 = st.columns(3)
        o["assets"] = c4.number_input("Kitchen Asset Value", value=o["assets"], step=1000.0)
        o["monthly_units"] = c5.number_input("Expected Monthly Units", value=int(o["monthly_units"]), step=10)
        o["dep_years"] = c6.slider("Depreciation Period (Years)", 1, 15, o["dep_years"])

        monthly_dep = rd(o["assets"] / (o["dep_years"] * 12))
        total_monthly_oh = o["rent"] + o["salaries"] + o["utilities"] + monthly_dep
        avg_oh_per_unit = rd(total_monthly_oh / o["monthly_units"]) if o["monthly_units"] > 0 else 0
        st.info(
            f"**Monthly Dep:** रू {monthly_dep} | **Total OH:** रू {total_monthly_oh} | **OH/Unit:** रू {avg_oh_per_unit}")

    # --- RECIPE SECTION ---
    st.subheader("🥣 Recipe Construction")
    if st.button("🔄 Sync Market Prices"):
        st.session_state.price_dict = load_market_prices()
        st.rerun()

    market_items = sorted([k.title() for k in st.session_state.price_dict.keys()])
    lid = st.session_state.load_id
    p_name = st.text_input("Product Name", value=st.session_state.editing_name, key=f"pn_{lid}")

    updated_buffer = []
    for i, row in enumerate(st.session_state.recipe_buffer):
        uid = row["id"]
        cur_val = row['item'].title()
        cols = st.columns([3, 1, 1, 1.5, 1.5, 0.5])

        opts = [""] + market_items
        if cur_val and cur_val not in opts: opts.append(cur_val)

        sel_item = cols[0].selectbox(f"Ingredient {i + 1}", opts,
                                     index=opts.index(cur_val) if cur_val in opts else 0,
                                     key=f"s_{uid}_{lid}")

        # Auto-update price if item changes
        if sel_item.lower() != row['item']:
            row['item'] = sel_item.lower()
            row['price'] = st.session_state.price_dict.get(sel_item.lower(), 0.0)
            row['v'] += 1
            st.rerun()

        qty = cols[1].number_input("Qty", 0.0, value=float(row['qty']), key=f"q_{uid}_{lid}", step=0.1)
        unit = cols[2].selectbox("Unit", ["g", "kg", "ml", "ltr", "pcs"], key=f"u_{uid}_{lid}",
                                 index=["g", "kg", "ml", "ltr", "pcs"].index(row['unit']))
        price = cols[3].number_input("Price/Unit", 0.0, value=float(row['price']), key=f"p_{uid}_{row['v']}_{lid}")

        row_tot = rd(qty * price)
        cols[4].markdown(f"**रू {row_tot}**")

        if cols[5].button("🗑️", key=f"del_{uid}_{lid}"):
            st.session_state.recipe_buffer = [r for r in st.session_state.recipe_buffer if r["id"] != uid]
            st.rerun()

        updated_buffer.append(
            {"id": uid, "item": sel_item.lower(), "qty": qty, "unit": unit, "price": price, "total": row_tot,
             "v": row['v']})

    st.session_state.recipe_buffer = updated_buffer
    if st.button("➕ Add Row"):
        st.session_state.recipe_buffer.append(
            {"id": str(uuid.uuid4()), "item": "", "qty": 0.0, "unit": "g", "price": 0.0, "v": 0})
        st.rerun()

    # --- STRATEGY & COSTING ---
    st.divider()
    strat = st.session_state.current_strategy
    f1, f2, f3, f4 = st.columns(4)
    yld = f1.number_input("Yield (Qty produced)", 0.01, value=float(strat.get("Yield", 1.0)), key=f"yld_{lid}")
    wst = f2.number_input("Waste %", 0.0, max_value=99.0, value=float(strat.get("Waste %", 5.0)), key=f"wst_{lid}")
    pkg = f3.number_input("Packaging/Unit", 0.0, value=float(strat.get("Pkg/Unit", 15.0)), key=f"pkg_{lid}")
    marg = f4.number_input("Margin %", 0.0, max_value=99.0, value=float(strat.get("Margin %", 50.0)), key=f"mr_{lid}")

    o_alloc = st.slider("OH Allocation % (How much of total OH this item bears)", 0, 200,
                        value=int(strat.get("OH Alloc %", 100)), key=f"o_{lid}")
    vat_on = st.checkbox("Apply 13% VAT", value=strat.get("VAT On", True), key=f"v_{lid}")

    # Calculations
    total_ingredients_cost = sum(r['total'] for r in st.session_state.recipe_buffer)
    # logic: Cost divided by (1-waste) then divided by yield
    unit_raw = rd((total_ingredients_cost / (1 - (wst / 100))) / yld)
    unit_oh = rd(avg_oh_per_unit * (o_alloc / 100))
    final_cost = rd(unit_raw + unit_oh + pkg)

    net_price = rd(final_cost / (1 - (marg / 100))) if marg < 100 else final_cost
    mrp = rd(net_price * 1.13) if vat_on else net_price

    # Metrics Display
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Raw Mat/Unit", f"रू {unit_raw}")
    m2.metric("Total Cost/Unit", f"रू {final_cost}")
    m3.metric("Net Price", f"रू {net_price}")
    m4.metric("VAT (13%)", f"रू {rd(mrp - net_price)}" if vat_on else "रू 0")
    m5.metric("Final MRP", f"रू {mrp}")

    # --- SAVE LOGIC ---
    st.write("###")
    if st.button("💾 SAVE & SYNC TO CLOUD", type="primary", use_container_width=True):
        info = {
            "Name": p_name, "Yield": yld, "Waste %": wst, "Pkg/Unit": pkg,
            "Margin %": marg, "OH Alloc %": o_alloc, "VAT On": vat_on,
            "MRP": mrp, "Total Cost": total_ingredients_cost, "Raw Mat/Unit": unit_raw
        }
        # Filter out empty rows
        rec_data = [{"item": i['item'], "qty": i['qty'], "unit": i['unit'], "price_per_unit": i['price']}
                    for i in st.session_state.recipe_buffer if i['item'] != ""]

        # Update session list
        idx = next((i for i, r in enumerate(st.session_state.master_records) if r["Info"]["Name"] == p_name), None)
        if idx is not None:
            st.session_state.master_records[idx] = {"Info": info, "Recipe": rec_data}
        else:
            st.session_state.master_records.append({"Info": info, "Recipe": rec_data})

        if save_all_to_sheets():
            st.session_state.save_success = True
            st.toast(f"Saved {p_name} to Google Sheets!")
            st.rerun()

    if st.session_state.save_success:
        st.success(f"**{p_name}** is now synced with the cloud!")


if __name__ == "__main__":
    bagels_co_master_engine()