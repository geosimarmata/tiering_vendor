import streamlit as st
import zipfile
import pandas as pd
import os
import shutil
import tempfile

st.set_page_config(page_title="Vendor Tiering System", layout="wide")
st.title("📦 Vendor Tiering System for JEJE")

# --- SESSION STATE INIT ---
for key in ["sheet_name", "combined_df", "tiered_df", "extract_dir", "sheet_names"]:
    if key not in st.session_state:
        st.session_state[key] = None

# --- SECTION 1: UPLOAD & READ SHEET NAMES ---
st.header("1️⃣ Upload ZIP and Read Excel Sheet Names")
uploaded_zip = st.file_uploader("Upload ZIP file containing vendor rate bids", type="zip")

if uploaded_zip and st.button("🔍 Extract & Read Sheet Names"):
    # Save zip to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded_zip.read())
        tmp_path = tmp.name

    # Remove old extracted folder
    if os.path.exists("bid_data"):
        try:
            shutil.rmtree("bid_data")
        except PermissionError:
            st.warning("Please close any open Excel files and try again.")
            st.stop()

    os.makedirs("bid_data", exist_ok=True)

    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
        zip_ref.extractall("bid_data")

    st.session_state.extract_dir = "bid_data"

    # Scan for all unique sheet names
    sheet_names = set()
    for root, _, files in os.walk("bid_data"):
        for file in files:
            if file.endswith(".xlsx"):
                try:
                    with pd.ExcelFile(os.path.join(root, file)) as xls:
                        sheet_names.update(xls.sheet_names)
                except Exception as e:
                    st.warning(f"Could not read {file}: {e}")

    st.session_state.sheet_names = sorted(list(sheet_names))

if st.session_state.sheet_names:
    st.session_state.sheet_name = st.selectbox("📄 Choose sheet to process", st.session_state.sheet_names)

# --- SECTION 2: GENERATE TIERING SYSTEM ---
st.header("2️⃣ Generate Tiering System")
if st.session_state.extract_dir and st.session_state.sheet_name:
    if st.button("⚙️ Generate Tiering System"):
        all_data = []
        for root, _, files in os.walk(st.session_state.extract_dir):
            for file in files:
                if file.endswith(".xlsx"):
                    try:
                        file_path = os.path.join(root, file)
                        with pd.ExcelFile(file_path) as xls:
                            if st.session_state.sheet_name in xls.sheet_names:
                                df = xls.parse(st.session_state.sheet_name, header=1)
                                df["file_name"] = file
                                all_data.append(df)
                    except Exception as e:
                        st.warning(f"Error reading {file}: {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            st.session_state.combined_df = combined_df

            # Run Tiering
            df = combined_df.copy()
            expected_cols = ['VENDOR', 'Origin City', 'Destination City', 'CDD', 'CDD LONG', 'CDE', 'CDE LONG', 'TRONTON WINGBOX', 'VAN BOX']
            missing_cols = [col for col in expected_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
            else:
                df = df.melt(
                    id_vars=['VENDOR', 'Origin City', 'Destination City'],
                    value_vars=['CDD', 'CDD LONG', 'CDE', 'CDE LONG', 'TRONTON WINGBOX', 'VAN BOX'],
                    var_name='truck_type',
                    value_name='price'
                ).dropna(subset=['price'])

                df = df.rename(columns={
                    'VENDOR': 'vendor',
                    'Origin City': 'origin_city',
                    'Destination City': 'destination_city'
                })

                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                df = df.dropna(subset=['price']).drop_duplicates()

                def assign_tiers(group):
                    group = group.sort_values(by="price").copy()
                    group["tier"] = ["Tier " + str(i + 1) for i in range(len(group))]
                    return group

                tiered_df = df.groupby(
                    ['truck_type', 'origin_city', 'destination_city'],
                    group_keys=False
                ).apply(assign_tiers)

                st.session_state.tiered_df = tiered_df[['truck_type', 'origin_city', 'destination_city', 'vendor', 'price', 'tier']]
                st.success("✅ Tiering system generated successfully!")

# --- SECTION 3: DISPLAY & DOWNLOAD ---
if st.session_state.tiered_df is not None:
    st.header("📊 Tiered Vendor Data Preview")

    df = st.session_state.tiered_df
    vendor_filter = st.selectbox("🔎 Filter by Vendor", ["All"] + sorted(df["vendor"].unique()))
    origin_filter = st.selectbox("📍 Filter by Origin City", ["All"] + sorted(df["origin_city"].unique()))
    destination_filter = st.selectbox("🎯 Filter by Destination City", ["All"] + sorted(df["destination_city"].unique()))

    filtered_df = df.copy()
    if vendor_filter != "All":
        filtered_df = filtered_df[filtered_df["vendor"] == vendor_filter]
    if origin_filter != "All":
        filtered_df = filtered_df[filtered_df["origin_city"] == origin_filter]
    if destination_filter != "All":
        filtered_df = filtered_df[filtered_df["destination_city"] == destination_filter]

    st.dataframe(filtered_df)

    st.download_button(
        label="⬇️ Download Filtered CSV",
        data=filtered_df.to_csv(index=False),
        file_name="tiered_vendor_data.csv",
        mime="text/csv"
    )
