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
    address_cols = pd.DataFrame(grouped_df['Address_List'].tolist(), index=grouped_df.index)
    if not address_cols.empty:
        address_cols.columns = [f'Address_{i+1}' for i in range(address_cols.shape[1])]
        final_df = pd.concat([grouped_df.drop(columns=['Address_List']), address_cols], axis=1)
    else:
        final_df = grouped_df.drop(columns=['Address_List'])

    # Add Phone Number column
    final_df.insert(1, 'Phone Number', '')

    return final_df

# Title
st.title("🎯 DoubleBarrel.Quest")
st.markdown("<h3 style='text-align: center; color: #94A3B8;'>Land Lease Contact Consolidation Tool</h3>", unsafe_allow_html=True)
st.markdown("---")

# Mode selection
st.markdown("### 🎨 Select Processing Mode")
st.markdown("Choose how to process your data:")

mode = st.radio(
    "Processing mode:",
    ["Consolidation with Multiple Addresses (Expanded)", "Consolidation with Address History"],
    index=0,
    label_visibility="collapsed"
)

st.markdown("---")

# Upload section with form
st.markdown("### 📤 Upload Your File")
st.markdown("**Required columns:** Grantor, Grantor Address, Instrument Date, Record Date, Section, Township, Area (Acres), County/Parish")

with st.form("land_lease_upload_form"):
    uploaded_file = st.file_uploader(
        "Upload your land lease file (.csv, .xls, .xlsx)",
        type=["csv", "xls", "xlsx"],
        accept_multiple_files=False
    )

    submitted = st.form_submit_button("🚀 Submit for Processing")

if submitted:
    if uploaded_file is None:
        st.error("❌ Please upload a CSV or Excel file before submitting.")
    else:
        filename = uploaded_file.name.lower()

        try:
            # Detect and read file
            if filename.endswith(".csv"):
                try:
                    df = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding="utf-8")
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            st.stop()

        st.success(f"✅ File received: {uploaded_file.name}")
        st.write(f"Detected **{len(df)}** rows and **{len(df.columns)}** columns.")
        
        # Preview data
        with st.expander("👁️ Preview uploaded data (first 10 rows)", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)

        # Run consolidation
        with st.spinner("⚙️ Consolidating landowner records..."):
            try:
                if mode == "Consolidation with Multiple Addresses (Expanded)":
                    result_df = consolidate_contacts_expanded_df(df)
                else:
                    # For now, use the same function for both modes
                    result_df = consolidate_contacts_expanded_df(df)
            except Exception as e:
                st.error(f"❌ Error during consolidation: {e}")
                st.info("Please ensure your CSV file has the required columns.")
                st.stop()

        st.success("✅ Consolidation complete! Download your consolidated file below.")
        st.write(f"Output rows: **{len(result_df)}**")
                
        # Show processing log
        original_count = len(df)
        consolidated_count = len(result_df)
        duplicates_removed = original_count - consolidated_count
        
        st.markdown("---")
        st.markdown("### 📊 Processing Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Entries", f"{original_count:,}")
        with col2:
            st.metric("Consolidated Contacts", f"{consolidated_count:,}")
        with col3:
            st.metric("Duplicates Removed", f"{duplicates_removed:,}", delta=f"-{duplicates_removed}")
        
        # Additional stats
        total_acres = result_df['Total Acres'].sum()
        unique_counties = result_df['Counties'].str.split(', ').explode().nunique()
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Total Acres", f"{total_acres:,.2f}")
        with col5:
            st.metric("Unique Counties", unique_counties)
        
        st.markdown("---")

        # Convert to CSV for download
        csv_bytes = result_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download Consolidated CSV",
            data=csv_bytes,
            file_name="Consolidated_Land_List_EXPANDED.csv",
            mime="text/csv"
        )
        
        # Preview consolidated data
        with st.expander("👁️ Preview consolidated data (first 10 rows)", expanded=False):
            st.dataframe(result_df.head(10), use_container_width=True)
else:
    st.info("👆 **Upload** your land lease CSV file to get started")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; opacity: 0.8;">'
    '🔒 Secure • 🎯 Professional • ⚡ Fast • 💯 100% Free<br>'
    '<strong>DoubleBarrel.Quest</strong> - Land Lease Contact Consolidation'
    '</p>',
    unsafe_allow_html=True
)
