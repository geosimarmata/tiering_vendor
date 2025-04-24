# Vendor Tiering System for JEJE
# Compatible with both localhost and Streamlit Community Cloud

import streamlit as st
import zipfile
import pandas as pd
import os
import shutil
import tempfile

# ------------------------ PAGE CONFIG ------------------------ #
st.set_page_config(page_title="Vendor Tiering System", layout="wide")

# ------------------------ SIDEBAR STYLE ------------------------ #
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #F27F30, #F97316, #CF3331);
        color: white;
    }
    div.stButton > button:first-of-type,
    div.stButton > button:last-of-type {
        background-color: #007AFF;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:first-of-type:hover,
    div.stButton > button:last-of-type:hover {
        background-color: #005BB5;
    }
    div[data-testid="stFileUploader"] {
        background-color: #FFE6E6;
        color: #333333;
        padding: 1em;
        border-radius: 10px;
        border: 1px solid #FFB3B3;
        margin-bottom: 1em;
    }
    .stFileUploader__fileName, .stFileUploader__instructions {
        color: #FF0000;
        font-weight: bold;
    }
    """,
    unsafe_allow_html=True
)

st.title("\U0001F4E6 Vendor Tiering System for JEJE")

# ------------------------ SESSION STATE INIT ------------------------ #
for key in ["sheet_names", "sheet_name", "extract_dir", "combined_df", "tiered_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------------ SIDEBAR INPUT ------------------------ #
uploaded_zip = st.sidebar.file_uploader("\U0001F4C1 Upload ZIP (Vendor Rate Bids)", type="zip")

if uploaded_zip and st.sidebar.button("\U0001F50D Extract & Load Sheets"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded_zip.read())
        tmp_path = tmp.name

    if os.path.exists("bid_data"):
        try:
            shutil.rmtree("bid_data")
        except PermissionError:
            st.warning("Please close any open Excel files and try again.")
            st.stop()

    os.makedirs("bid_data", exist_ok=True)

    with st.spinner("Extracting ZIP..."):
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            zip_ref.extractall("bid_data")
    st.success("\u2705 ZIP extracted successfully.")
    st.session_state.extract_dir = "bid_data"

    sheet_names = set()
    excel_files = []
    for root, _, files in os.walk("bid_data"):
        for file in files:
            if file.endswith(".xlsx"):
                excel_files.append(os.path.join(root, file))

    with st.spinner("Reading sheet names from Excel files..."):
        for file_path in excel_files:
            try:
                with pd.ExcelFile(file_path) as xls:
                    sheet_names.update(xls.sheet_names)
            except Exception as e:
                st.warning(f"Failed reading {os.path.basename(file_path)}: {e}")

    st.session_state.sheet_names = sorted(list(sheet_names))
    st.success(f"\u2705 Found {len(st.session_state.sheet_names)} unique sheet(s).")

# ------------------------ SELECT SHEET ------------------------ #
desired_sheets = ["OH!SOME", "SPX FTL", "LOTTE"]
if st.session_state.sheet_names:
    filtered_sheet_names = [s for s in st.session_state.sheet_names if s in desired_sheets]
else:
    filtered_sheet_names = []

if uploaded_zip and st.session_state.sheet_names:
    if filtered_sheet_names:
        st.session_state.sheet_name = st.sidebar.selectbox("\U0001F4C4 Select Sheet to Process", filtered_sheet_names)
#    else:
#        st.warning("No matching sheets found. Please check the uploaded files.")

# ------------------------ GENERATE TIERING ------------------------ #
all_data = []
if st.session_state.extract_dir and st.session_state.sheet_name:
    if st.sidebar.button("\u2699\ufe0f Generate Tiering System"):
        excel_files = []
        for root, _, files in os.walk(st.session_state.extract_dir):
            for file in files:
                if file.endswith(".xlsx"):
                    excel_files.append(os.path.join(root, file))

        with st.spinner("Processing files..."):
            for file_path in excel_files:
                try:
                    with pd.ExcelFile(file_path) as xls:
                        if st.session_state.sheet_name in xls.sheet_names:
                            df = xls.parse(st.session_state.sheet_name, header=1)
                            df["file_name"] = os.path.basename(file_path)
                            all_data.append(df)
                except Exception as e:
                    st.warning(f"Error reading {os.path.basename(file_path)}: {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            st.session_state.combined_df = combined_df
            df = combined_df.copy()

            predefined_truck_types = ['VAN BOX', 'BLINDVAN', 'CDE', 'CDE LONG', 'CDD', 'CDD LONG', 'FUSO', 'FUSO LONG', 'TRONTON WINGBOX']
            df.columns = df.columns.str.strip().str.replace(r"Unnamed: \\d+", "", regex=True).str.replace(r"#REF!", "", regex=True).str.replace(r"\\.+$", "", regex=True)

            id_columns = ['VENDOR', 'Origin City', 'Destination City']
            truck_type_columns = [col for col in df.columns if col in predefined_truck_types]

            if not truck_type_columns:
                st.error("\u274C No valid truck type columns found in the data.")
            else:
                df = df.melt(id_vars=id_columns, value_vars=truck_type_columns, var_name='truck_type', value_name='price')
                df = df.rename(columns={'VENDOR': 'vendor', 'Origin City': 'origin_city', 'Destination City': 'destination_city'})
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                df = df.dropna(subset=['price']).drop_duplicates()

                def assign_tiers(group):
                    group = group.sort_values(by="price").copy()
                    unique_prices = group["price"].unique()
                    price_to_tier = {price: f"Tier {i + 1}" for i, price in enumerate(unique_prices)}
                    group["tier"] = group["price"].map(price_to_tier)
                    return group

                tiered_df = df.groupby(['truck_type', 'origin_city', 'destination_city'], group_keys=False).apply(assign_tiers)
                st.session_state.tiered_df = tiered_df[['truck_type', 'origin_city', 'destination_city', 'vendor', 'price', 'tier']]
                st.success("\u2705 Tiering system generated!")

# ------------------------ DATA PREVIEW & FILTER ------------------------ #
if st.session_state.tiered_df is not None:
    st.header("\U0001F4CA Tiered Vendor Data Preview")
    df = st.session_state.tiered_df

    vendor_filter = st.sidebar.selectbox("\U0001F50E Filter by Vendor", ["All"] + sorted(df["vendor"].unique()))
    origin_filter = st.sidebar.selectbox("\U0001F4CD Filter by Origin City", ["All"] + sorted(df["origin_city"].unique()))
    destination_filter = st.sidebar.selectbox("\U0001F3AF Filter by Destination City", ["All"] + sorted(df["destination_city"].unique()))

    filtered_df = df.copy()
    if vendor_filter != "All":
        filtered_df = filtered_df[filtered_df["vendor"] == vendor_filter]
    if origin_filter != "All":
        filtered_df = filtered_df[filtered_df["origin_city"] == origin_filter]
    if destination_filter != "All":
        filtered_df = filtered_df[filtered_df["destination_city"] == destination_filter]

    filtered_df = filtered_df.rename(columns={
        "origin_city": "Origin",
        "destination_city": "Destination",
        "price": "Transport Price",
        "vendor": "Transporter",
        "tier": "Tiering"
    })
    filtered_df = filtered_df[["Origin", "Destination", "Transport Price", "Transporter", "Tiering"]]
    filtered_df["Status"] = "Active"
    filtered_df["Transport Price"] = filtered_df["Transport Price"].astype(int)

    st.dataframe(filtered_df)
    st.download_button(
        label="\U0001F4E5 Download Tiering Result (CSV)",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name="tiered_vendor_data.csv",
        mime="text/csv"
    )
