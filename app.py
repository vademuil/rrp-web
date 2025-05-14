
import streamlit as st
import pandas as pd
import requests
import io
from group_currency_data import CURRENCY_GROUPS, BASE_CURRENCY_BY_GROUP

VAT_BY_COUNTRY = {
    'us': 0, 'eu': 21, 'gb': 20, 'ru': 20, 'cn': 13, 'au': 10, 'br': 17,
    'ca': 5, 'jp': 10, 'mx': 16, 'kr': 10, 'tr': 18, 'za': 15, 'ch': 8,
    'in': 18, 'pl': 23, 'nzd': 15, 'nok': 25, 'kz': 12, 'ua': 20
}

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
        return data[str(app_id)]["data"]["price_overview"]["initial"] / 100
    except:
        return None

def get_exchange_rates():
    url = "https://api.exchangerate.host/latest?base=EUR"
    r = requests.get(url)
    return r.json().get("rates", {})

def find_group_and_base(currency):
    for group, currencies in CURRENCY_GROUPS.items():
        if currency in currencies:
            return group, BASE_CURRENCY_BY_GROUP.get(group)
    return None, None

def calculate_adjusted_prices(base_price, ssrp_df, partner_percent, rates, currencies):
    ref_prices = ssrp_df["us"].astype(float)
    closest_idx = (ref_prices - base_price).abs().idxmin()
    selected_row = ssrp_df.loc[closest_idx].astype(float)

    rows = []
    for country in selected_row.index:
        try:
            currency = currencies.reset_index(drop=True)[selected_row.index.get_loc(country)].strip().upper()
            vat = VAT_BY_COUNTRY.get(country.lower(), 0)
            srp = float(selected_row[country])
            net_local = srp / (1 + vat / 100) * (partner_percent / 100)
            rate = rates.get(currency, None)
            if not rate:
                continue
            net_eur = round(net_local / rate, 4)
            group, base_currency = find_group_and_base(currency)
            if not group or not base_currency:
                continue
            rows.append({
                "Country": country.upper(),
                "Currency": currency,
                "VAT %": vat,
                "Original SRP": srp,
                "Net Local": round(net_local, 2),
                "Net EUR": net_eur,
                "Rate": rate,
                "Group": group,
                "Base Currency": base_currency
            })
        except:
            continue

    if not rows:
        st.warning("Нет строк для расчёта. Проверьте SSRP и группы валют.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    for group, group_df in df.groupby("Group"):
        base_currency = group_df["Base Currency"].iloc[0]
        base_val = group_df[group_df["Currency"] == base_currency]["Net EUR"].mean()
        df.loc[group_df.index, "Δ from base (%)"] = ((group_df["Net EUR"] - base_val) / base_val * 100).round(2)
        df.loc[group_df.index, "Adj Net EUR"] = group_df["Net EUR"].where(
            (group_df["Net EUR"] >= base_val) |
            ((group_df["Net EUR"] - base_val) / base_val * 100).abs() <= 5,
            other=base_val
        )

    df["Adj Net Local"] = df["Adj Net EUR"] * df["Rate"]
    df["Final SRP"] = df.apply(
        lambda x: round(x["Adj Net Local"] / (partner_percent / 100) * (1 + x["VAT %"] / 100), 2), axis=1
    )
    df["Adjusted"] = df["Net EUR"] != df["Adj Net EUR"]
    return df

st.title("Steam Partner Price Calculator")
app_id = st.text_input("Steam App ID")
partner_share = st.number_input("Partner Share (%)", min_value=1, max_value=100, value=70)

if app_id:
    base_price = fetch_steam_price(app_id)
    if base_price:
        st.success(f"Base SRP from Steam: ${base_price:.2f}")
        ssrp_df, country_codes, currencies = load_ssrp()
        rates = get_exchange_rates()
        df = calculate_adjusted_prices(base_price, ssrp_df, partner_share, rates, currencies)
        if not df.empty:
            st.dataframe(df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Download Excel", output.getvalue(), "final_prices.xlsx")
    else:
        st.error("Не удалось получить цену из Steam. Проверьте App ID.")
