import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="DoubleBarrel.Quest – Land Lease Consolidation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# STYLES
# -------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    h1, h2, h3 {
        color: #00D9FF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# CORE LOGIC
# -------------------------------------------------
def consolidate_contacts_expanded_df(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [
        'Grantor', 'Grantor Address',
        'Instrument Date', 'Record Date',
        'Section', 'Township',
        'Area (Acres)', 'County/Parish'
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Normalize
    df['Grantor_Clean'] = df['Grantor'].astype(str).str.strip().str.upper()
    df['Address_Clean'] = df['Grantor Address'].astype(str).str.strip().str.upper()

    # Activity date (newest wins)
    df['Sort_Date'] = pd.to_datetime(df['Instrument Date'], errors='coerce')
    df['Sort_Date'] = df['Sort_Date'].fillna(
        pd.to_datetime(df['Record Date'], errors='coerce')
    )

    # -------- Level 1: True Dupes (Person + Address) --------
    def aggregate_person_address(group):
        parcels = []
        for _, r in group.iterrows():
            s = str(r['Section']).strip() if pd.notna(r['Section']) else ""
            t = str(r['Township']).strip() if pd.notna(r['Township']) else ""
            if s or t:
                parcels.append(f"{s} ({t})")

        return pd.Series({
            "Grantor Name": group['Grantor'].iloc[0],
            "Grantor Address": group['Grantor Address'].iloc[0],
            "Total Acres": group['Area (Acres)'].fillna(0).sum(),
            "Parcels List": " | ".join(sorted(set(parcels))),
            "Counties": ", ".join(sorted(group['County/Parish'].dropna().unique())),
            "Last Activity": group['Sort_Date'].max()
        })

    address_level = (
        df
        .groupby(['Grantor_Clean', 'Address_Clean'], as_index=False)
        .apply(aggregate_person_address)
        .reset_index(drop=True)
    )

    # -------- Level 2: Person Consolidation --------
    def aggregate_person(group):
        group = group.sort_values("Last Activity", ascending=False)
        addresses = group["Grantor Address"].tolist()

        address_cols = {
            f"Address_{i+1}": addr
            for i, addr in enumerate(addresses)
        }

        return pd.Series({
            "Grantor Name": group["Grantor Name"].iloc[0],
            "Phone Number": "",
            "Total Acres": group["Total Acres"].sum(),
            "Parcels List": " | ".join(sorted(set(
                " | ".join(group["Parcels List"]).split(" | ")
            ))),
            "Counties": ", ".join(sorted(set(
                ", ".join(group["Counties"]).split(", ")
            ))),
            **address_cols
        })

    final_df = (
        address_level
        .groupby("Grantor_Clean", as_index=False)
        .apply(aggregate_person)
        .reset_index(drop=True)
    )

    return final_df


def calculate_metrics(raw_df, result_df):
    metrics = {
        "before": len(raw_df),
        "after": len(result_df),
        "removed": len(raw_df) - len(result_df),
        "total_acres": None
    }

    # Safely detect acres column
    for col in result_df.columns:
        if col.strip().lower() == "total acres":
            metrics["total_acres"] = result_df[col].fillna(0).sum()
            break

    return metrics


# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🎯 DoubleBarrel.Quest")
st.markdown(
    "<h3 style='text-align:center;color:#94A3B8;'>Land Lease Contact Consolidation</h3>",
    unsafe_allow_html=True
)
st.markdown("---")

with st.expander("🧠 How duplicates are defined"):
    st.markdown("""
    **A duplicate is defined as:**
    - Same Grantor
    - Same Grantor Address

    **What this tool does:**
    - Consolidates mineral interests **per address**
    - Preserves **multiple addresses**
    - Orders addresses **newest → oldest**
    - Sums acreage safely
    - Never drops ownership data
    """)

st.markdown("### 📤 Upload Land Lease File")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xls", "xlsx"]
)

if uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    st.success(f"Loaded {len(df)} records")

    with st.expander("Preview Input"):
        st.dataframe(df.head(10), use_container_width=True)

    with st.spinner("⚙️ Consolidating records..."):
        result_df = consolidate_contacts_expanded_df(df)
        metrics = calculate_metrics(df, result_df)

    st.success("✅ Consolidation Complete")

    st.markdown("### 📊 Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records Before", metrics["before"])
    c2.metric("Records After", metrics["after"])
    c3.metric("Duplicates Collapsed", metrics["removed"])
    if metrics["total_acres"] is not None:
    c4.metric("Total Acres", f"{metrics['total_acres']:,.2f}")
else:
    c4.metric("Total Acres", "N/A")


    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Consolidated CSV",
        data=csv,
        file_name="DoubleBarrel_Consolidated.csv",
        mime="text/csv"
    )

    with st.expander("Preview Output"):
        st.dataframe(result_df.head(10), use_container_width=True)
else:
    st.info("👆 Upload a file to begin")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;opacity:0.8;'>"
    "🔒 Secure • 🎯 Land-Grade Logic • ⚡ Fast<br>"
    "<strong>DoubleBarrel.Quest</strong>"
    "</p>",
    unsafe_allow_html=True
)
