# 📦 Vendor Tiering System Dashboard

A Streamlit web application designed to help logistics and procurement teams process vendor bid data from Excel files, analyze transport pricing, and assign vendor tier rankings for decision-making.

---

## 📝 Project Overview

This dashboard allows users to upload a ZIP file containing multiple Excel spreadsheets of vendor rate bids. It extracts and processes the data, identifies relevant information for selected shippers, and automatically ranks vendors based on their pricing.

Users can interactively filter the results, preview the tiered vendor data, and download the processed output as a CSV file for further reporting or use.

---

## 🚀 Key Features

- 🔄 Upload ZIP files containing multiple `.xlsx` vendor bid files
- 📄 Automatically extract and scan for sheets like `"OH!SOME"`, `"SPX FTL"`, `"LOTTE"`
- 📊 Process and merge data from all relevant sheets
- 📉 Automatically assign tier levels based on price (lowest = Tier 1, etc.)
- 🔍 Interactive filtering by:
  - Vendor
  - Origin city
  - Destination city
- ⬇️ Download filtered data in a clean, standardized format

---

## 📂 Folder and File Expectations

- The ZIP file should contain one or more `.xlsx` files.
- Each Excel file must include a sheet with one of the supported names (`OH!SOME`, `SPX FTL`, or `LOTTE`).
- Excel sheets should contain:
  - Vendor names
  - Origin and destination cities
  - Transport pricing for various truck types

---

## 📦 Output Data Includes

| Column           | Description                         |
|------------------|-------------------------------------|
| Shipper          | Name of the selected sheet/shipper  |
| Type Truck       | Type of vehicle used for transport  |
| Origin           | Starting city for delivery          |
| Destination      | Target delivery city                |
| Transport Price  | Price quoted by vendor              |
| Transporter      | Vendor name                         |
| Tiering          | Tier level assigned (Tier 0–n)      |
| Status           | Currently fixed to "Active"         |

---

## 🛠 Built With

- Python 3.x
- [Streamlit](https://streamlit.io/)
- pandas
- zipfile, shutil, os (for file and folder handling)

---

## ▶️ How to Use

1. Visit the live app (if deployed on Streamlit Cloud)
2. Upload a ZIP file with vendor bid spreadsheets
3. Select the shipper (sheet name) to process
4. Click **Generate Tiering System**
5. Filter the data as needed
6. Download the results as a CSV file

---

## 📌 Use Cases

- Vendor performance comparison
- Logistics cost optimization
- Internal procurement support
- Dashboard-based tier mapping for management reports

---

## 👤 Author

Developed by Geo Saragih 
Feel free to explore, use, and extend this tool.

---

## 🧾 License

This project is open-source and free to use under the MIT License.
