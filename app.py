import streamlit as st
import pandas as pd

# =================================================
# CONFIG
# =================================================
DUPE_LOGIC_VERSION = "address_v1_strict"
MAX_ADDRESSES = 5     # increase if needed
MAX_COUNTIES = 3      # CRM-safe limit

st.set_page_config(
    page_title="DoubleBarrel.Quest – Zoho-Ready Consolidation",
    page_icon="🎯",
    layout="wide"
)

# =================================================
# CORE CONSOLIDATION LOGIC
# =================================================
def consolidate_for_zoho(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [
        "Grantor", "Grantor Address",
        "Instrument Date", "Record Date",
        "Section", "Township",
        "Area (Acres)", "County/Parish"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Normalize identity
    df["Grantor_Clean"] = df["Grantor"].astype(str).str.strip().str.upper()
    df["Address_Clean"] = df["Grantor Address"].astype(str).str.strip().str.upper()

    # Activity date
    df["Sort_Date"] = pd.to_datetime(df["Instrument Date"], errors="coerce")
    df["Sort_Date"] = df["Sort_Date"].fillna(
        pd.to_datetime(df["Record Date"], errors="coerce")
    )

    # -------- LEVEL 1: TRUE DUPES (Grantor + Address) --------
    def agg_person_address(g):
        parcels = []
        for _, r in g.iterrows():
            s = str(r["Section"]).strip() if pd.notna(r["Section"]) else ""
            t = str(r["Township"]).strip() if pd.notna(r["Township"]) else ""
            if s or t:
                parcels.append(f"{s} ({t})")

        return pd.Series({
            "Grantor Name": g["Grantor"].iloc[0],
            "Address": g["Grantor Address"].iloc[0],
            "Address_Acres": g["Area (Acres)"].fillna(0).sum(),
            "Address_Parcels": ", ".join(sorted(set(parcels))),
            "County_List": ", ".join(sorted(g["County/Parish"].dropna().unique())),
            "Last_Activity": g["Sort_Date"].max()
        })

    address_level = (
        df
        .groupby(["Grantor_Clean", "Address_Clean"], as_index=False)
        .apply(agg_person_address)
        .reset_index(drop=True)
    )

    # -------- LEVEL 2: OWNER → FLAT CRM ROW --------
    def agg_owner(g):
        g = g.sort_values("Last_Activity", ascending=False)

        out = {
            "Owner_Name": g["Grantor Name"].iloc[0],
            "Phone": "",
            "Total_Acres": g["Address_Acres"].sum(),
            "Dupe_Logic_Version": DUPE_LOGIC_VERSION
        }

        # Counties (flat)
        counties = sorted(set(
            ", ".join(g["County_List"]).split(", ")
        ))[:MAX_COUNTIES]

        for i, c in enumerate(counties, start=1):
            out[f"County_{i}"] = c

        # Addresses (flat, numbered)
        for i, row in enumerate(g.itertuples(index=False), start=1):
            if i > MAX_ADDRESSES:
                break
            out[f"Address_{i}"] = row.Address
            out[f"Address_{i}_Acres"] = row.Address_Acres
            out[f"Address_{i}_Parcels"] = row.Address_Parcels

        return pd.Series(out)

    final_df = (
        address_level
        .groupby("Grantor_Clean", as_index=False)
        .apply(agg_owner)
        .reset_index(drop=True)
    )

    return final_df, address_level


# ===========
