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
    /* Sidebar background with orange gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #FF8C00, #FFA500);  /* Orange gradient */
        color: white;
    }

    /* Sidebar buttons (using red for buttons) */
    div.stButton > button {
        background-color: #FF0000;  /* Strong Red */
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #FF4500;  /* Lighter red-orange hover */
        color: white;
    }

    /* Main area file uploader background */
    div[data-testid="stFileUploader"] {
        background-color: #FFE6E6;  /* Soft light pink background */
        color: #333333;  /* Dark text for file name */
        padding: 1em;
        border-radius: 10px;
        border: 1px solid #FFB3B3;  /* Lighter red border */
        margin-bottom: 1em;
    }

    /* File name text color */
    div[data-testid="stFileUploader"] .stFileUploader__fileName {
        color: #333333;  /* Darker text */
    }

    /* File uploader instruction text color */
    div[data-testid="stFileUploader"] .stFileUploader__instructions {
        color: #FF0000;  /* Red text for instructions */
        font-weight: bold;
    }

    /* Custom styling for the upload ZIP section */
    .stFileUploader__input {
        background-color: #FFE6E6;  /* Light pink background */
        color: #333333;  /* Dark text */
        border-radius: 10px;
        padding: 1em;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.title("📦 Vendor Tiering System for JEJE")

# ------------------------ SESSION STATE INIT ------------------------ #
for key in ["sheet_names", "sheet_name", "extract_dir", "combined_df", "tiered_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------------ SIDEBAR INPUT ------------------------ #
uploaded_zip = st.sidebar.file_uploader("📁 Upload ZIP (Vendor Rate Bids)", type="zip")

if uploaded_zip and st.sidebar.button("🔍 Extract & Load Sheets"):
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
    st.success("✅ ZIP extracted successfully.")

    st.session_state.extract_dir = "bid_data"

    # Read sheet names
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
    st.success(f"✅ Found {len(st.session_state.sheet_names)} unique sheet(s).")

# ------------------------ SELECT SHEET ------------------------ #
if st.session_state.sheet_names:
    st.session_state.sheet_name = st.sidebar.selectbox("📄 Select Sheet to Process", st.session_state.sheet_names)

# ------------------------ GENERATE TIERING ------------------------ #
if st.session_state.extract_dir and st.session_state.sheet_name:
    if st.sidebar.button("⚙️ Generate Tiering System"):
        all_data = []
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
            expected_cols = ['VENDOR', 'Origin City', 'Destination City', 'CDD', 'CDD LONG', 'CDE', 'CDE LONG', 'TRONTON WINGBOX', 'VAN BOX']
            missing_cols = [col for col in expected_cols if col not in df.columns]

            if missing_cols:
                st.error(f"❌ Missing required columns: {missing_cols}")
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
                st.success("✅ Tiering system generated!")

# ------------------------ DATA PREVIEW & FILTER ------------------------ #
if st.session_state.tiered_df is not None:
    st.header("📊 Tiered Vendor Data Preview")
    df = st.session_state.tiered_df

    vendor_filter = st.sidebar.selectbox("🔎 Filter by Vendor", ["All"] + sorted(df["vendor"].unique()))
    origin_filter = st.sidebar.selectbox("📍 Filter by Origin City", ["All"] + sorted(df["origin_city"].unique()))
    destination_filter = st.sidebar.selectbox("🎯 Filter by Destination City", ["All"] + sorted(df["destination_city"].unique()))

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
