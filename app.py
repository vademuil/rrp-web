
import streamlit as st
import pandas as pd
import requests
import io

# Load SSRP.csv from local path
@st.cache_data
def load_ssrp():
    df = pd.read_csv("SSRP.csv", sep=";", header=None)
    countries = df.iloc[1, :]
    currencies = df.iloc[2, :]
    prices = df.iloc[3:, :].reset_index(drop=True)
    prices.columns = countries
    return prices, countries, currencies

# Fetch price from Steam API
def fetch_steam_price(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    try:
        price = data[str(app_id)]["data"]["price_overview"]["initial"] / 100
        return price
    except:
        return None

# Calculate recommended prices
def calculate_prices(base_price, ssrp_df):
    # Найти ближайшую цену в первой колонке (us)
    ref_prices = ssrp_df["us"].astype(float)
    closest_idx = (ref_prices - base_price).abs().idxmin()
    selected_row = ssrp_df.loc[closest_idx].astype(float)

    # Применим условный VAT (пример: 20%) и округление
    vat_by_country = {
        "eu": 0.20, "gb": 0.20, "ru": 0.20, "tr": 0.18, "jp": 0.10,
        "us": 0.0, "cn": 0.0, "ua": 0.20, "br": 0.15
    }

    prices = []
    for country, price in selected_row.items():
        vat = vat_by_country.get(country, 0.0)
        final_price = round(price * (1 + vat), 2)
        prices.append((country.upper(), final_price))

    return pd.DataFrame(prices, columns=["Country", "Final Price"])

# UI
st.title("Steam Price Recommendation Tool")
app_id = st.text_input("Enter Steam App ID:", "")

if app_id:
    with st.spinner("Fetching base price from Steam..."):
        base_price = fetch_steam_price(app_id)

    if base_price is None:
        st.error("❌ Could not fetch base price for this App ID.")
    else:
        st.success(f"Base price (USD): ${base_price:.2f}")
        ssrp_df, _, _ = load_ssrp()
        result_df = calculate_prices(base_price, ssrp_df)

        st.dataframe(result_df)

        # Download as Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("📥 Download as Excel", output.getvalue(), "prices.xlsx")
