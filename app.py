
import streamlit as st
import pandas as pd
import requests
import io
from group_currency_data import CURRENCY_GROUPS, BASE_CURRENCY_BY_GROUP

# VAT по странам
VAT_BY_CURRENCY = {
    "EUR": 0.21, "USD": 0.0, "GBP": 0.20, "RUB": 0.20, "CNY": 0.13,
    "BRL": 0.17, "PLN": 0.23, "TRY": 0.18, "KRW": 0.10, "JPY": 0.10,
    "INR": 0.18, "UAH": 0.20, "CAD": 0.05, "AUD": 0.10, "CHF": 0.08,
    "NOK": 0.25, "NZD": 0.15, "HKD": 0.0, "SGD": 0.08
}

@st.cache_data
def load_ssrp():
    df = pd.read_csv("SSRP.csv", sep=";", header=None)
    countries = df.iloc[1, :]
    currencies = df.iloc[2, :]
    prices = df.iloc[3:, :].reset_index(drop=True)
    prices.columns = countries
    return prices, countries, currencies

def get_usd_price(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us"
    r = requests.get(url)
    data = r.json()
    try:
        price = data[str(app_id)]["data"]["price_overview"]["initial"] / 100
        return round(price, 2)
    except:
        return None

def get_exchange_rates():
    url = "https://api.exchangerate.host/latest?base=EUR"
    r = requests.get(url)
    return r.json().get("rates", {})

def find_price_row(ssrp_df, usd_price):
    ref_prices = ssrp_df["us"].astype(float)
    closest_idx = (ref_prices - usd_price).abs().idxmin()
    return ssrp_df.loc[closest_idx].astype(float)

def calculate_net_prices(price_row, currencies, partner_percent, rates):
    result = []
    for idx, (country, srp) in enumerate(price_row.items()):
        currency = currencies.reset_index(drop=True)[idx].strip().upper()
        vat = VAT_BY_CURRENCY.get(currency, 0)
        rate = rates.get(currency, None)
        if rate is None or rate == 0:
            continue
        net = srp / (1 + vat) * (partner_percent / 100)
        net_eur = net / rate
        result.append({
            "Country": country.upper(),
            "Currency": currency,
            "Original SRP": srp,
            "VAT": vat,
            "Net": round(net, 4),
            "Net EUR": round(net_eur, 4),
            "Rate": rate
        })
    return pd.DataFrame(result)

def normalize_by_group(df, partner_percent):
    df["Group"] = df["Currency"].apply(lambda c: next((g for g, lst in CURRENCY_GROUPS.items() if c in lst), None))
    df["Base Currency"] = df["Group"].map(BASE_CURRENCY_BY_GROUP)
    df["Base Net EUR"] = df.apply(
        lambda row: df[(df["Group"] == row["Group"]) & (df["Currency"] == row["Base Currency"])]["Net EUR"].mean(),
        axis=1
    )
    df["Δ %"] = ((df["Net EUR"] - df["Base Net EUR"]) / df["Base Net EUR"] * 100).round(2)
    df["Adjusted Net EUR"] = df.apply(
        lambda row: row["Base Net EUR"] if row["Δ %"] < -5 else row["Net EUR"], axis=1
    )
    df["Adjusted"] = df["Adjusted Net EUR"] > df["Net EUR"]
    df["Adjusted Net"] = df["Adjusted Net EUR"] * df["Rate"]
    df["Final SRP"] = df.apply(
        lambda row: round(row["Adjusted Net"] / (partner_percent / 100) * (1 + row["VAT"]), 2), axis=1
    )
    return df

st.title("Steam SRP Recalculator")

app_id = st.text_input("Enter Steam App ID")
partner_share = st.number_input("Partner Share %", value=70, min_value=1, max_value=100)

if app_id:
    usd_price = get_usd_price(app_id)
    if not usd_price:
        st.error("Could not fetch price from Steam")
    else:
        st.success(f"Base price in USD: ${usd_price}")
        ssrp_df, _, currencies = load_ssrp()
        rates = get_exchange_rates()
        row = find_price_row(ssrp_df, usd_price)
        df = calculate_net_prices(row, currencies, partner_share, rates)
        df = normalize_by_group(df, partner_share)

        def highlight_adj(s):
            return ["background-color: #C6EFCE" if adj else "" for adj in s]

        st.dataframe(df.style.apply(highlight_adj, subset=["Adjusted"], axis=1))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        st.download_button("Download Excel", output.getvalue(), "srp_adjusted.xlsx")
