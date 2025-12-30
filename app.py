import streamlit as st
import pandas as pd

# =================================================
# CONFIG
# =================================================
DUPE_LOGIC_VERSION = "address_v1_strict"

st.set_page_config(
    page_title="DoubleBarrel.Quest – Land Lease Consolidation",
    page_icon="🎯",
    layout="wide"
)

# =================================================
# CORE LOGIC
# =================================================
def consolidate_contacts(df: pd.DataFrame):
    required_cols = [
        "Grantor", "Grantor Address",
        "Instrument Date", "Record Date",
        "Section", "Township",
        "Area (Acres)", "County/Parish"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Normalize
    df["Grantor_Clean"] = df["Grantor"].astype(str).str.strip().str.upper()
    df["Address_Clean"] = df["Grantor Address"].astype(str).str.strip().str.upper()

    # Activity date
    df["Sort_Date"] = pd.to_datetime(df["Instrument Date"], errors="coerce")
    df["Sort_Date"] = df["Sort_Date"].fillna(
        pd.to_datetime(df["Record Date"], errors="coerce")
    )

    # ---------- LEVEL 1: PERSON + ADDRESS ----------
    def agg_person_address(g):
        parcels = []
        for _, r in g.iterrows():
            s = str(r["Section"]).strip() if pd.notna(r["Section"]) else ""
            t = str(r["Township"]).strip() if pd.notna(r["Township"]) else ""
            if s or t:
                parcels.append(f"{s} ({t})")

        return pd.Series({
            "Grantor Name": g["Grantor"].iloc[0],
            "Grantor Address": g["Grantor Address"].iloc[0],
            "Address Acres": g["Area (Acres)"].fillna(0).sum(),
            "Address Parcels": " | ".join(sorted(set(parcels))),
            "Counties": ", ".join(sorted(g["County/Parish"].dropna().unique())),
            "Last Activity": g["Sort_Date"].max()
        })

    address_level = (
        df
        .groupby(["Grantor_Clean", "Address_Clean"], as_index=False)
        .apply(agg_person_address)
        .reset_index(drop=True)
    )

    # ---------- LEVEL 2: PERSON ----------
    def agg_person(g):
        g = g.sort_values("Last Activity", ascending=False)

        out = {
            "Grantor Name": g["Grantor Name"].iloc[0],
            "Phone Number": "",
            "Total Acres": g["Address Acres"].sum(),
            "Counties": ", ".join(sorted(set(
                ", ".join(g["Counties"]).split(", ")
            ))),
            "Dupe_Logic_Version": DUPE_LOGIC_VERSION
        }

        for i, row in enumerate(g.itertuples(index=False), start=1):
            out[f"Address_{i}"] = row._2
            out[f"Address_{i}_Acres"] = row._3
            out[f"Address_{i}_Parcels"] = row._4

        return pd.Series(out)

    final_df = (
        address_level
        .groupby("Grantor_Clean", as_index=False)
        .apply(agg_person)
        .reset_index(drop=True)
    )

    return final_df, address_level


# =================================================
# METRICS (NO COLUMN ASSUMPTIONS)
# =================================================
def calculate_metrics(raw_df, address_level_df, final_df):
    return {
        "records_before": len(raw_df),
        "records_after": len(final_df),
        "duplicates_collapsed": len(raw_df) - len(final_df),
        "total_acres": address_level_df["Address Acres"].sum()
    }


# =================================================
# UI
# =================================================
st.title("🎯 DoubleBarrel.Quest")
st.markdown("**Land-Grade Landowner Consolidation**")
st.markdown("---")

with st.expander("🧠 Duplicate Logic (Audit Safe)"):
    st.markdown(f"""
    **Version:** `{DUPE_LOGIC_VERSION}`

    - Duplicate = Same Grantor **AND** Same Address
    - Minerals & acres consolidated per address
    - Multiple addresses preserved (newest → oldest)
    - No ownership data dropped
    """)

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
        st.error(f"File error: {e}")
        st.stop()

    st.success(f"Loaded {len(df)} rows")

    with st.expander("Preview Input"):
        st.dataframe(df.head(10), use_container_width=True)

    with st.spinner("⚙️ Consolidating…"):
        final_df, address_level = consolidate_contacts(df)
        metrics = calculate_metrics(df, address_level, final_df)

    st.success("✅ Consolidation Complete")

    # -------- METRICS --------
    st.markdown("### 📊 Summary")
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Records Before", metrics["records_before"])
    c2.metric("Records After", metrics["records_after"])
    c3.metric("Duplicates Collapsed", metrics["duplicates_collapsed"])
    c4.metric("Total Acres", f"{metrics['total_acres']:,.2f}")

    # -------- DOWNLOAD --------
    csv = final_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Consolidated CSV",
        data=csv,
        file_name="DoubleBarrel_Consolidated_AuditSafe.csv",
        mime="text/csv"
    )

    with st.expander("Preview Output"):
        st.dataframe(final_df.head(10), use_container_width=True)

else:
    st.info("👆 Upload a file to begin")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;opacity:0.8;'>"
    "🔒 Audit-Safe • 🎯 Address-Strict • ⚡ Land-Grade<br>"
    "<strong>DoubleBarrel.Quest</strong>"
    "</p>",
    unsafe_allow_html=True
)
