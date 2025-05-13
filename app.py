
import streamlit as st
import pandas as pd
import requests
import io

@st.cache_data
def load_ssrp():
    df = pd.read_csv("SSRP.csv", sep=";", header=None)
    countries = df.iloc[1, :]
    currencies = df.iloc[2, :]
    prices = df.iloc[3:, :].reset_index(drop=True)
    prices.columns = countries
    return prices, countries, currencies

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

def calculate_prices(base_price, ssrp_df):
    ref_prices = ssrp_df["us"].astype(float)
    closest_idx = (ref_prices - base_price).abs().idxmin()
    selected_row = ssrp_df.loc[closest_idx].astype(float)

    vat_by_country = {
        "eu": 0.20, "gb": 0.20, "ru": 0.20, "tr": 0.18, "jp": 0.10,
        "us": 0.0, "cn": 0.0, "ua": 0.20, "br": 0.15
    }

    countries = selected_row.index
    original_prices = selected_row.values
    final_prices = []
    percents = []

    for country in countries:
        original_price = selected_row[country]
        vat = vat_by_country.get(country, 0.0)
        final_price = round(original_price * (1 + vat), 2)
        final_prices.append(final_price)

        percent_diff = ((final_price - original_price) / original_price) * 100 if original_price != 0 else 0
        percents.append(round(percent_diff, 2))

    result_df = pd.DataFrame({
        "Country": countries.str.upper(),
        "Original SSRP Price": original_prices,
        "Final Price (with VAT)": final_prices,
        "Change (%)": percents
    })

    return result_df

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

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("📥 Download as Excel", output.getvalue(), "prices_detailed.xlsx")
