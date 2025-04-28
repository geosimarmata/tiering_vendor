# The Revised Little from app.py

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
    /* Sidebar background with smooth gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #F27F30, #F97316, #CF3331);  /* Smooth gradient */
        color: white;
    }
    
    <style>
    /* Hide Streamlit menu (three dots) */
    #MainMenu {visibility: hidden;}

    /* Hide Streamlit footer (GitHub logo and fork button) */
    footer {visibility: hidden;}    

    /* Extract button (blue) */
    div.stButton > button:first-of-type {
        background-color: #007AFF;  /* Blue color */
        color: white;  /* White text */
        border-radius: 8px;
        padding: 0.5em 1em;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:first-of-type:hover {
        background-color: #005BB5;  /* Darker blue on hover */
        color: white;  /* White text */
    }

    /* Generate button (blue) */
    div.stButton > button:last-of-type {
        background-color: #007AFF;  /* Blue color */
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:last-of-type:hover {
        background-color: #005BB5;  /* Darker blue on hover */
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
# Filter sheet names to include only specific ones
desired_sheets = ["OH!SOME", "SPX FTL", "LOTTE"]

if st.session_state.sheet_names:  # Ensure sheet names are loaded
    filtered_sheet_names = [sheet for sheet in st.session_state.sheet_names if sheet in desired_sheets]
else:
    filtered_sheet_names = []

if uploaded_zip and st.session_state.sheet_names:  # Only show the select box if sheets are loaded
    if filtered_sheet_names:
        st.session_state.sheet_name = st.sidebar.selectbox("📄 Select Shipper", filtered_sheet_names)
    else:
        # Display a warning with the file names that were processed
        st.warning(
            f"No matching sheets found in the uploaded files. "
            f"Processed files: {', '.join([os.path.basename(file) for file in excel_files])}"
        )
        
# Initialize all_data as an empty list
all_data = []
# ------------------------ GENERATE TIERING ------------------------ #
if st.session_state.extract_dir and st.session_state.sheet_name:
    if st.sidebar.button("⚙️ Generate Tiering System"):
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
                            df["shipper"] = st.session_state.sheet_name
                            all_data.append(df)
                except Exception as e:
                    st.warning(f"Error reading {os.path.basename(file_path)}: {e}")

# ...existing code...

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            st.session_state.combined_df = combined_df

            df = combined_df.copy()

            # Predefined truck types
            predefined_truck_types = ['VAN BOX', 'BLINDVAN', 'CDE', 'CDE LONG', 'CDD', 'CDD LONG', 'FUSO', 'FUSO LONG', 'TRONTON WINGBOX']

            # Clean column names to remove "Unnamed" and "#REF!"
            df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
            df.columns = df.columns.str.replace(r"Unnamed: \d+", "", regex=True)  # Remove "Unnamed: X"
            df.columns = df.columns.str.replace(r"#REF!", "", regex=True)  # Remove "#REF!"
            df.columns = df.columns.str.replace(r"\.+$", "", regex=True)  # Remove trailing dots

            # Required ID columns
            id_columns = ['VENDOR', 'Origin City', 'Destination City']

            # Dynamically detect truck type columns (intersection with predefined truck types)
            truck_type_columns = [col for col in df.columns if col in predefined_truck_types]

            if not truck_type_columns:
                st.error("❌ No valid truck type columns found in the data. Please check the uploaded files.")
            else:
                # Reshape the data based on detected truck types
                df = df.melt(
                    id_vars=id_columns + ['shipper'],
                    value_vars=truck_type_columns,
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
                    # Separate rows where the vendor is "SJL/JHT"
                    sjl_jht_rows = group[group["vendor"].str.contains("SJL|JHT", case=False, na=False)].copy()
                    other_rows = group[~group["vendor"].str.contains("SJL|JHT", case=False, na=False)].copy()

                    # Assign Tier 0 to SJL/JHT rows
                    sjl_jht_rows["tier"] = "Tier 0"

                    # Sort other rows by price and assign tiers starting from Tier 1
                    other_rows = other_rows.sort_values(by="price").copy()
                    unique_prices = other_rows["price"].unique()
                    price_to_tier = {price: f"Tier {i + 1}" for i, price in enumerate(unique_prices)}
                    other_rows["tier"] = other_rows["price"].map(price_to_tier)

                    # Combine the two DataFrames back together
                    return pd.concat([sjl_jht_rows, other_rows], ignore_index=True)

                tiered_df = df.groupby(
                    ['truck_type', 'origin_city', 'destination_city'],
                    group_keys=False
                ).apply(assign_tiers)

                st.session_state.tiered_df = tiered_df[['shipper', 'truck_type', 'origin_city', 'destination_city', 'vendor', 'price', 'tier']]
                st.success("✅ Tiering system generated!")
        
        
# ------------------------ DATA PREVIEW & FILTER ------------------------ #
if st.session_state.tiered_df is not None:
    st.header("📊 Tiered Vendor Data Preview")
    df = st.session_state.tiered_df

    # Sidebar filters
    vendor_filter = st.sidebar.selectbox("🔎 Filter by Vendor", ["All"] + sorted(df["vendor"].unique()))
    origin_filter = st.sidebar.selectbox("📍 Filter by Origin City", ["All"] + sorted(df["origin_city"].unique()))
    destination_filter = st.sidebar.selectbox("🎯 Filter by Destination City", ["All"] + sorted(df["destination_city"].unique()))

    # Apply filters
    filtered_df = df.copy()
    if vendor_filter != "All":
        filtered_df = filtered_df[filtered_df["vendor"] == vendor_filter]
    if origin_filter != "All":
        filtered_df = filtered_df[filtered_df["origin_city"] == origin_filter]
    if destination_filter != "All":
        filtered_df = filtered_df[filtered_df["destination_city"] == destination_filter]

    # Reset the index to exclude the index column from the CSV
    filtered_df = filtered_df.reset_index(drop=True)

    # Rename columns and reorder them
    filtered_df = filtered_df.rename(columns={
        "origin_city": "Origin",
        "destination_city": "Destination",
        "price": "Transport Price",
        "vendor": "Transporter",
        "tier": "Tiering",
        "truck_type": "Type Truck",
        'shipper': 'Shipper'
    })
    filtered_df = filtered_df[['Shipper', "Type Truck", "Origin", "Destination", "Transport Price", "Transporter", "Tiering"]]

    # Add a "Status" column with the value "Active" (can be commented out if not needed)
    filtered_df["Status"] = "Active"

    # Format the "Transport Price" column to remove ".0"
    filtered_df["Transport Price"] = filtered_df["Transport Price"].astype(int)

    # Display the filtered dataframe
    st.dataframe(filtered_df)

    # Download button for the filtered CSV
    st.download_button(
        label="⬇️ Download Tiered Vendor Data",
        data=filtered_df.to_csv(index=False),  # Ensure index is excluded
        file_name="tiered_vendor_data.csv",
        mime="text/csv"
    )
