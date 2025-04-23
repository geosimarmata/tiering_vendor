import streamlit as st
import zipfile
import pandas as pd
import os

# Step 1: File Upload
st.title("Vendor Tiering System")
st.markdown("Upload the ZIP file containing the vendor rate bid data to process and tier the routes.")

# Upload ZIP file
uploaded_zip = st.file_uploader("Choose a ZIP file", type="zip")

if uploaded_zip is not None:
    # Save the uploaded file to the current working directory
    temp_zip_path = "temp.zip"
    with open(temp_zip_path, "wb") as f:
        f.write(uploaded_zip.getbuffer())

    # Extract ZIP file
    extract_dir = "bid_data"  # Create this directory for extracted files
    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    st.success("ZIP file extracted successfully!")

    # Function to read the "ALL TP KKV" sheet from Excel files
    def read_all_sheets(file_path):
        try:
            xl = pd.ExcelFile(file_path)
            if 'ALL TP KKV' in xl.sheet_names:
                # Read with header=1 assuming the header is in the second row (index 1)
                df = xl.parse('ALL TP KKV', header=1)
                df['file_name'] = os.path.basename(file_path)
                return df
        except Exception as e:
            st.error(f"Failed to read {file_path}: {e}")
        return None

    # Step 2: Collect data from the ZIP file
    all_data = [
        read_all_sheets(os.path.join(root, file))
        for root, _, files in os.walk(extract_dir)
        for file in files if file.endswith(".xlsx")
    ]

    all_data = [df for df in all_data if df is not None]

    # Step 3: Combine data into a single DataFrame
    combined_df = pd.concat(all_data, ignore_index=True)

    # Show preview of the combined data
    st.subheader("Preview of Combined Data")
    st.dataframe(combined_df.head())

    # Step 4: Check the column names to ensure correctness
    st.subheader("Column Names in Data")
    st.write(combined_df.columns)

    # Step 5: Process the relevant columns and reshape the DataFrame
    relevant_cols = ['VENDOR', 'Origin City', 'Destination City', 'CDD', 'CDD LONG', 'CDE', 'CDE LONG', 'TRONTON WINGBOX', 'VAN BOX']
    
    # Check if relevant columns exist
    if all(col in combined_df.columns for col in relevant_cols):
        df = combined_df[relevant_cols].copy()
    else:
        st.error(f"Some of the relevant columns are missing: {set(relevant_cols) - set(combined_df.columns)}")
        st.stop()

    # Melt the DataFrame to unpivot the truck types
    melted_df = df.melt(
        id_vars=['VENDOR', 'Origin City', 'Destination City'],
        value_vars=['CDD', 'CDD LONG', 'CDE', 'CDE LONG', 'TRONTON WINGBOX', 'VAN BOX'],
        var_name='truck_type',
        value_name='price'
    ).dropna(subset=['price'])

    # Clean and rename columns
    melted_df = melted_df.rename(columns={
        'VENDOR': 'vendor',
        'Origin City': 'origin_city',
        'Destination City': 'destination_city'
    })

    melted_df['price'] = pd.to_numeric(melted_df['price'], errors='coerce')
    melted_df = melted_df.dropna(subset=['price']).drop_duplicates()

    # Step 6: Assign tiers based on price
    def assign_tiers(df):
        df = df.sort_values(by='price').copy()
        price_to_tier = {price: f'Tier {i+1}' for i, price in enumerate(sorted(df['price'].unique()))}
        df['tier'] = df['price'].map(price_to_tier)
        return df

    # Apply tier assignment
    tiered_df = melted_df.groupby(['truck_type', 'origin_city', 'destination_city'], group_keys=False).apply(assign_tiers)

    # Reorder columns for display
    tiered_df = tiered_df[['truck_type', 'origin_city', 'destination_city', 'vendor', 'price', 'tier']]

    # Step 7: Filter by Vendor, Origin, or Destination City
    st.sidebar.header("Filters")

    vendors = tiered_df['vendor'].unique()
    selected_vendor = st.sidebar.selectbox("Select Vendor", ["All Vendors"] + list(vendors))

    origin_cities = tiered_df['origin_city'].unique()
    selected_origin = st.sidebar.selectbox("Select Origin City", ["All Cities"] + list(origin_cities))

    destination_cities = tiered_df['destination_city'].unique()
    selected_destination = st.sidebar.selectbox("Select Destination City", ["All Cities"] + list(destination_cities))

    # Apply filters
    filtered_df = tiered_df
    if selected_vendor != "All Vendors":
        filtered_df = filtered_df[filtered_df['vendor'] == selected_vendor]
    if selected_origin != "All Cities":
        filtered_df = filtered_df[filtered_df['origin_city'] == selected_origin]
    if selected_destination != "All Cities":
        filtered_df = filtered_df[filtered_df['destination_city'] == selected_destination]

    # Display the filtered data first
    st.subheader("Filtered Tiered Data")
    st.dataframe(filtered_df)

    # Step 8: Display Tiered Data at the bottom
    st.subheader("Tiered Vendor Data")
    st.dataframe(tiered_df)

    # Step 9: Download the filtered data
    st.subheader("Download Filtered Data")
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="filtered_vendor_data.csv",
        mime="text/csv"
    )
