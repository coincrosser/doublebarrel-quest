import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="DoubleBarrel.Quest - Land Lease Consolidation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# DOUBLEBARREL.QUEST Brand Colors
st.markdown(
    """
    <style>
    /* Dark theme matching logo */
    .main {
        background: linear-gradient(135deg, #0A1628 0%, #1a2642 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #0A1628 0%, #1a2642 100%);
    }
    
    /* Title with cyan glow */
    h1 {
        color: #00D9FF !important;
        text-align: center;
        font-size: 3.5rem !important;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
        font-weight: 900 !important;
    }
    
    .subtitle {
        color: #FF6600;
        text-align: center;
        font-size: 1.3rem;
        margin-bottom: 2rem;
        text-shadow: 0 0 10px rgba(255, 102, 0, 0.3);
    }
    
    /* Upload box */
    .upload-box {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 217, 255, 0.2);
        border: 2px solid rgba(0, 217, 255, 0.3);
    }
    
    /* All text white */
    p, span, div, label {
        color: white !important;
    }
    
    /* Radio buttons */
    .stRadio > label {
        color: white !important;
        font-size: 1.1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Logo
st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 1.5rem;">
            <div style="width: 80px; height: 80px; border-radius: 50%; background: #000000; border: 4px solid #00FFFF; box-shadow: 0 0 20px #00FFFF; animation: pulse 2s ease-in-out infinite;"></div>
            <div style="width: 80px; height: 80px; border-radius: 50%; background: #000000; border: 4px solid #FF8C00; box-shadow: 0 0 20px #FF8C00; animation: pulse 2s ease-in-out infinite;"></div>
        </div>
        <div style="font-family: 'Courier New', monospace; font-size: 1.8rem; font-weight: bold; color: white; letter-spacing: 3px;">DOUBLEBARREL.QUEST</div>
    </div>
""", unsafe_allow_html=True)

st.markdown(
    '<p class="subtitle">• Land Lease Contact Consolidation • Multi-Mode Processing •</p>',
    unsafe_allow_html=True,
)

# Main container
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    
    # Mode selection
    st.markdown("### 🎯 Select Processing Mode")
    mode = st.radio(
        "Choose how to process your data:",
        ["Consolidation with Multiple Addresses (Expanded)", "Consolidation with Address History"]
    )
    
    st.markdown("---")
    st.markdown("### 📤 Upload Your CSV File")
    st.markdown("**Required columns:** Grantor, Grantor Address, Instrument Date, Record Date, Section, Township, Area (Acres), County/Parish")
    
    uploaded_file = st.file_uploader(
        "",
        type=["csv"],
        help="Upload your land lease CSV file"
    )
    
    if uploaded_file is not None:
        try:
            # Read the file
            with st.spinner('🔵 Loading your data...'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
            
            st.success(f"✅ **Loaded:** {uploaded_file.name}")
            st.info(f"📊 **Original Entries:** {len(df):,} | **Columns:** {len(df.columns)}")
            
            # Show preview
            with st.expander("👁️ Preview Original Data (first 5 rows)"):
                st.dataframe(df.head(), use_container_width=True)
            
            # Process based on mode
            with st.spinner('🔍 Consolidating contacts...'):
                if mode == "Consolidation with Multiple Addresses (Expanded)":
                    # MODE 1: Expanded Addresses
                    df['Grantor_Clean'] = df['Grantor'].astype(str).str.strip().str.upper()
                    df['Sort_Date'] = pd.to_datetime(df['Instrument Date'], errors='coerce')
                    df['Sort_Date'] = df['Sort_Date'].fillna(pd.to_datetime(df['Record Date'], errors='coerce'))
                    
                    def aggregate_grantor(group):
                        group = group.sort_values('Sort_Date')
                        
                        # Get Unique Addresses
                        seen_addrs = set()
                        unique_addrs = []
                        for addr in group['Grantor Address']:
                            if pd.notna(addr) and str(addr).strip() != "":
                                addr_str = str(addr).strip()
                                if addr_str not in seen_addrs:
                                    unique_addrs.append(addr_str)
                                    seen_addrs.add(addr_str)
                        
                        # Get Unique Parcels
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
                    
                    grouped_df = df.groupby('Grantor_Clean').apply(aggregate_grantor).reset_index(drop=True)
                    
                    # Expand addresses to columns
                    address_cols = pd.DataFrame(grouped_df['Address_List'].tolist(), index=grouped_df.index)
                    new_col_names = [f'Address_{i+1}' for i in range(address_cols.shape[1])]
                    address_cols.columns = new_col_names
                    
                    df_consolidated = pd.concat([grouped_df.drop(columns=['Address_List']), address_cols], axis=1)
                    df_consolidated.insert(1, 'Phone Number', '')
                    
                else:
                    # MODE 2: Address History
                    df['Grantor_Clean'] = df['Grantor'].astype(str).str.strip().str.upper()
                    df['Sort_Date'] = pd.to_datetime(df['Instrument Date'], errors='coerce')
                    df['Sort_Date'] = df['Sort_Date'].fillna(pd.to_datetime(df['Record Date'], errors='coerce'))
                    
                    def consolidate_row(group):
                        group = group.sort_values('Sort_Date')
                        
                        # Get Unique Addresses
                        seen_addrs = set()
                        unique_addrs = []
                        for addr in group['Grantor Address']:
                            if pd.notna(addr) and addr not in seen_addrs:
                                unique_addrs.append(str(addr))
                                seen_addrs.add(addr)
                        
                        # Get Unique Parcels
                        group['Parcel_Info'] = group['Section'].astype(str) + " (" + group['Township'].astype(str) + ")"
                        unique_parcels = group['Parcel_Info'].unique()
                        
                        return pd.Series({
                            'Grantor Name': group['Grantor'].iloc[0],
                            'Row Count': len(group),
                            'Address History (Oldest -> Newest)': " | ".join(unique_addrs),
                            'Current/Last Known Address': unique_addrs[-1] if unique_addrs else "",
                            'Parcels Owned (Section/Twp)': " | ".join(unique_parcels),
                            'Total Acres': group['Area (Acres)'].sum(),
                            'Counties': ", ".join(group['County/Parish'].unique()),
                            'Phone Number': ''
                        })
                    
                    df_consolidated = df.groupby('Grantor_Clean').apply(consolidate_row).reset_index(drop=True)
            
            st.success(f"✅ **Consolidation Complete!** Created {len(df_consolidated):,} unique contacts from {len(df):,} entries")
            
            # Show results
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric("Original Entries", f"{len(df):,}")
            
            with col_b:
                st.metric("Unique Contacts", f"{len(df_consolidated):,}")
            
            st.markdown("---")
            st.markdown("### 🎯 Download Consolidated Data")
            
            # Prepare download
            consolidated_csv = df_consolidated.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Consolidated Contact List",
                data=consolidated_csv,
                file_name=f"Consolidated_{uploaded_file.name}",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
            
            # Preview consolidated data
            with st.expander("👁️ Preview Consolidated Data (first 10 rows)"):
                st.dataframe(df_consolidated.head(10), use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ **Error:** {str(e)}")
            st.info("Please ensure your CSV file has the required columns.")
    
    else:
        st.info("👆 **Upload** your land lease CSV file to get started")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; opacity: 0.8;">'
    '🔒 Secure • 🎨 Professional • ⚡ Fast • 🆓 100% Free<br>'
    '<strong>DoubleBarrel.Quest</strong> - Land Lease Contact Consolidation'
    '</p>',
    unsafe_allow_html=True
)
