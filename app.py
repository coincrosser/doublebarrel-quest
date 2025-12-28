import streamlit as st
import pandas as pd
from io import StringIO
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="DoubleBarrel.Quest - Land Lease Consolidation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# DOUBLEBARREL.QUEST Branding
st.markdown(
    """
    <style>
    /* Dark theme matching */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Title with cyan accent */
    h1 {
        color: #00D9FF !important;
        text-align: center;
        font-size: 3.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Subheader styling */
    h2, h3 {
        color: #00D9FF !important;
    }
    
    /* Upload section */
    .uploadedFile {
        background: rgba(0, 217, 255, 0.1) !important;
        border: 2px solid #00D9FF !important;
        border-radius: 10px !important;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(90deg, #00D9FF 0%, #0EA5E9 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(0, 217, 255, 0.3) !important;
    }
    
    /* Download button */
    .stDownloadButton>button {
        background: linear-gradient(90deg, #10B981 0%, #059669 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Consolidation function
def consolidate_contacts_expanded_df(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure the key columns exist
    required_cols = [
        'Grantor', 'Instrument Date', 'Record Date',
        'Grantor Address', 'Section', 'Township',
        'Area (Acres)', 'County/Parish'
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Standardize Names for Grouping
    df['Grantor_Clean'] = df['Grantor'].astype(str).str.strip().str.upper()

    # Build a sort date
    df['Sort_Date'] = pd.to_datetime(df['Instrument Date'], errors='coerce')
    df['Sort_Date'] = df['Sort_Date'].fillna(
        pd.to_datetime(df['Record Date'], errors='coerce')
    )

    # Define aggregation logic
    def aggregate_grantor(group):
        group = group.sort_values('Sort_Date')

        # Unique addresses in order
        seen_addrs = set()
        unique_addrs = []
        for addr in group['Grantor Address']:
            if pd.notna(addr) and str(addr).strip() != "":
                addr_str = str(addr).strip()
                if addr_str not in seen_addrs:
                    unique_addrs.append(addr_str)
                    seen_addrs.add(addr_str)

        # Unique parcel strings
        group['Section'] = group['Section'].fillna('')
        group['Township'] = group['Township'].fillna('')
        parcel_strs = []
        for _, row in group.iterrows():
            s = str(row['Section']).strip()
            t = str(row['Township']).strip()
            if s or t:
                parcel_strs.append(f"{s} ({t})")
        unique_parcels = sorted(list(set(parcel_strs)))

        return pd.Series({
            'Grantor Name': group['Grantor'].iloc[0],
            'Total Acres': group['Area (Acres)'].sum(),
            'Counties': ", ".join(sorted(group['County/Parish'].dropna().unique())),
            'Parcels List': " | ".join(unique_parcels),
            'Address_List': unique_addrs
        })

    grouped_df = df.groupby('Grantor_Clean', as_index=False).apply(aggregate_grantor)
    grouped_df = grouped_df.reset_index(drop=True)

    # Expand Address_List into Address_1, Address_2, ...
        # ROBUST: Expand Address_List into Address_1, Address_2, ... columns
    # Find the maximum number of addresses any grantor has
    max_addresses = grouped_df['Address_List'].apply(len).max()
    
    # Create individual Address columns by extracting from list
    for i in range(max_addresses):
        grouped_df[f'Address_{i+1}'] = grouped_df['Address_List'].apply(
                lambda addr_list: addr_list[i] if i < len(addr_list) else "")    # Drop the Address_List column now that we've expanded it
    final_df = grouped_df.drop(columns=['Address_List'])

    # Add Phone Number column
    final_df.insert(1, 'Phone Number', '')

    return final_df
# Title
st.title("🎯 DoubleBarrel.Quest")
st.markdown("<h3 style='text-align: center; color: #94A3B8;'>Land Lease Contact Consolidation Tool</h3>", unsafe_allow_html=True)
st.markdown("---")
