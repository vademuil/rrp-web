
import streamlit as st
import pandas as pd

@st.cache_data
def load_ssrp():
    df = pd.read_csv("SSRP.csv", sep=";", header=None)
    countries = df.iloc[1]
    currencies = df.iloc[2]
    prices = df.iloc[3:].reset_index(drop=True)
    prices.columns = countries
    return prices, countries, currencies

st.title("Steam Price Viewer")

app_id = st.text_input("Enter Steam App ID")
partner_share = st.number_input("Partner Share (%)", min_value=1, max_value=100, value=70)

if app_id:
    try:
        prices_df, countries, currencies = load_ssrp()
        base_prices = prices_df["us"].astype(float)
        base_price = base_prices.median()  # временно используем медиану
        closest_row = prices_df.iloc[(base_prices - base_price).abs().idxmin()]
        df = pd.DataFrame({
            "Country": closest_row.index,
            "Currency": [currencies[i].strip().upper() for i in range(len(closest_row))],
            "SRP": closest_row.values
        })
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error reading data: {e}")
