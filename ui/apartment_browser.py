import streamlit as st
import pandas as pd
import os
import sys

# Set page configuration
st.set_page_config(page_title="Apartment Browser", page_icon="🏢", layout="wide")

# Set path to CSV file
csv_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "output", "filtered_apartments.csv"
)


def load_data():
    """Load the apartment data from CSV file"""
    try:
        df = pd.read_csv(csv_path)
        # Convert price to numeric (remove CHF and apostrophes)
        df["price_numeric"] = (
            df["price_details"]
            .str.extract(r"CHF\s+([\d\']+)")
            .iloc[:, 0]
            .str.replace("'", "")
            .astype(float)
        )
        # Extract number of rooms from title
        df["rooms"] = df["title"].str.extract(r"(\d+(?:\s*½)?)\s*Zimmer").iloc[:, 0]
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def main():
    st.title("Apartment Browser")
    st.write("Browse and filter available apartments")

    # Load data
    df = load_data()

    if df.empty:
        st.warning("No apartment data available")
        return

    # Create filters in the sidebar
    st.sidebar.header("Filter Options")

    # Price range filter
    if "price_numeric" in df.columns:
        min_price = int(df["price_numeric"].min())
        max_price = int(df["price_numeric"].max())
        price_range = st.sidebar.slider(
            "Price Range (CHF)", min_price, max_price, (min_price, max_price)
        )
        df = df[
            (df["price_numeric"] >= price_range[0])
            & (df["price_numeric"] <= price_range[1])
        ]

    # City filter
    if "city_info" in df.columns and not df["city_info"].isna().all():
        cities = ["All"] + sorted(df["city_info"].dropna().unique().tolist())
        selected_city = st.sidebar.selectbox("City", cities)
        if selected_city != "All":
            df = df[df["city_info"] == selected_city]

    # Feature filters
    st.sidebar.subheader("Features")

    feature_columns = [
        "pets_allowed",
        "bath_has_window",
        "kitchen_floor_not_wood",
        "has_dishwasher",
        "has_washingmachine",
        "has_balcony",
    ]

    selected_features = {}
    for feature in feature_columns:
        display_name = " ".join(feature.split("_")).title()
        selected_features[feature] = st.sidebar.checkbox(display_name)

    # Apply feature filters
    for feature, selected in selected_features.items():
        if selected:
            df = df[df[feature] == True]

    # Display number of results
    st.write(f"Found {len(df)} apartments matching your criteria")

    # Display the data
    # Create a multi-select for columns to display
    default_columns = [
        "title",
        "price_details",
        "street",
        "city_info",
        "meets_all_criteria",
    ]
    all_columns = df.columns.tolist()
    selected_columns = st.multiselect(
        "Select columns to display", all_columns, default=default_columns
    )

    if not selected_columns:
        selected_columns = default_columns

    # Add a URL column with clickable links
    df_display = df[selected_columns].copy()
    if "url" not in selected_columns:
        df_display["url"] = df["url"]

    # Convert URLs to clickable links
    df_display["url"] = df_display["url"].apply(
        lambda x: f'<a href="{x}" target="_blank">View</a>'
    )

    # Display the table with sorting
    st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Alternative display option with st.dataframe for better interactivity
    st.subheader("Interactive Table (click column headers to sort)")
    st.dataframe(df[selected_columns], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
