import streamlit as st
import pandas as pd

# ===============================
# CONFIG
# ===============================
DUPE_LOGIC_VERSION = "address_v1_strict"
MAX_ADDRESSES = 5
MAX_COUNTIES = 3

st.set_page_config(
    page_title="DoubleBarrel.Quest – Zoho Ready",
    page_icon="🎯",
    layout="wide"
)

# ===============================
# CONSOLIDATION LOGIC
# ===============================
def consolidate_for_zoho(df: pd.DataFrame):

    required_cols = [
        "Grantor", "Grantor Address",
        "Instrument Date", "Record Date",
        "Section", "Township",
        "Area (Acres)", "County/Parish"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # Normalize
    df["Grantor_Clean"] = df["Grantor"].astype(str).str.upper().str.strip()
    df["Address_Clean"] = df["Grantor Address"].astype(str).str.upper().str.strip()

    # Activity date
    df["Sort_Date"] = pd.to_datetime(df["Instrument Date"], errors="coerce")
    df["Sort_Date"] = df["Sort_Date"].fillna(
        pd.to_datetime(df["Record Date"], errors="coerce")
    )

    # ---------- Address-level ----------
    address_rows = []
    for (_, _), g in df.groupby(["Grantor_Clean", "Address_Clean"]):
        parcels = []
        for _, r in g.iterrows():
            s = str(r["Section"]).strip()
            t = str(r["Township"]).strip()
            if s or t:
                parcels.append(f"{s} ({t})")

        address_rows.append({
            "Grantor": g["Grantor"].iloc[0],
            "Address": g["Grantor Address"].iloc[0],
            "Address_Acres": pd.to_numeric(g["Area (Acres)"], errors="coerce").fillna(0).sum(),
            "Address_Parcels": ", ".join(sorted(set(parcels))),
            "Counties": ", ".join(sorted(g["County/Parish"].dropna().unique())),
            "Last_Activity": g["Sort_Date"].max()
        })

    address_df = pd.DataFrame(address_rows)

    # ---------- Owner-level (flat CRM row) ----------
    final_rows = []

    for owner, g in address_df.groupby("Grantor"):
        g = g.sort_values("Last_Activity", ascending=False)

        row = {
            "Owner_Name": owner,
            "Phone": "",
            "Total_Acres": g["Address_Acres"].sum(),
            "Dupe_Logic_Version": DUPE_LOGIC_VERSION
        }

        counties = sorted(
            set(", ".join(g["Counties"]).split(", "))
        )[:MAX_COUNTIES]

        for i, c in enumerate(counties, 1):
            row[f"County_{i}"] = c

        for i, (_, r) in enumerate(g.iterrows(), 1):
            if i > MAX_ADDRESSES:
                break
            row[f"Address_{i}"] = r["Address"]
            row[f"Address_{i}_Acres"] = r["Address_Acres"]
            row[f"Address_{i}_Parcels"] = r["Address_Parcels"]

        final_rows.append(row)

    return pd.DataFrame(final_rows), address_df


# ===============================
# UI
# ===============================
st.title("🎯 DoubleBarrel.Quest")
st.markdown("**Zoho-Ready Landowner Consolidation**")
st.markdown("---")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xls", "xlsx"]
)

if uploaded_file:
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"Loaded {len(df)} records")

    with st.spinner("Consolidating…"):
        final_df, address_df = consolidate_for_zoho(df)

    st.success("✅ Complete")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input Rows", len(df))
    c2.metric("Owners", len(final_df))
    c3.metric("Addresses", len(address_df))
    c4.metric("Total Acres", f"{address_df['Address_Acres'].sum():,.2f}")

    csv = final_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Zoho-Ready CSV",
        csv,
        "DoubleBarrel_Zoho.csv",
        "text/csv"
    )

    st.dataframe(final_df.head(10), use_container_width=True)

else:
    st.info("Upload a file to begin")
