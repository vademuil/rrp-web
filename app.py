import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="RRP Converter", layout="wide")
st.title("💱 RRP Price Converter with VAT")

EXCHANGE_API_URL = "https://api.exchangeratesapi.io/v1/latest"
ACCESS_KEY = "3a7e501b0c4bacf8817fa3d87fa15661"

COUNTRY_DATA = {
    "us": {"region": "EUROPE", "name": "United States", "vat": 0},
    "eu": {"region": "EUROPE", "name": "European Union", "vat": 21},
    "ru": {"region": "CIS", "name": "Russia", "vat": 20},
    "cn": {"region": "ASIA", "name": "China", "vat": 13},
    "gb": {"region": "EUROPE", "name": "United Kingdom", "vat": 20},
}

uploaded_file = st.file_uploader("Upload SSRP.csv file", type=["csv"])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file, sep=';', header=None)
    st.write("### 📊 Raw Data Preview", df_raw.head())

    country_codes = df_raw.iloc[0].tolist()
    currencies = df_raw.iloc[1].tolist()
    data = df_raw.iloc[2:].reset_index(drop=True)
    data.columns = country_codes

    st.write("\nFetching latest exchange rates...")
    response = requests.get(EXCHANGE_API_URL, params={"access_key": ACCESS_KEY})
    if response.status_code == 200:
        rates = response.json().get("rates", {})

        wb = Workbook()
        ws = wb.active
        ws.title = "RRP Converted"

        ws.append(country_codes)
        ws.append(currencies)
        for row in data.values:
            ws.append(row.tolist())

        fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        for cell in ws[1]:
            cell.fill = fill

        output = BytesIO()
        wb.save(output)
        st.success("✅ Excel file generated!")

        st.download_button(
            label="📥 Download Excel file",
            data=output.getvalue(),
            file_name="converted_rrp.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Failed to fetch exchange rates from API.")
