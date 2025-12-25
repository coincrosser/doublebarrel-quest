import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="DoubleBarrel.Quest - Duplicate Remover",
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
    
    /* Logo container */
    .logo-container {
        text-align: center;
        padding: 2rem 0 1rem 0;
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
    
    /* Success boxes with cyan */
    .stSuccess {
        background: rgba(0, 217, 255, 0.1);
        border-left: 4px solid #00D9FF;
        color: white;
    }
    
    /* Warning boxes with orange */
    .stWarning {
        background: rgba(255, 102, 0, 0.1);
        border-left: 4px solid #FF6600;
        color: white;
    }
    
    /* Info boxes */
    .stInfo {
        background: rgba(0, 217, 255, 0.05);
        border-left: 4px solid #00D9FF;
        color: white;
    }
    
    /* Download buttons with cyan/orange theme */
    .stDownloadButton button {
        background: linear-gradient(135deg, #00D9FF 0%, #FF6600 100%);
        color: white;
        border: none;
        font-weight: bold;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #00D9FF;
        font-size: 2rem;
    }
    
    /* All text white */
    p, span, div {
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Logo and Title
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
# Try video first (animated logo), then fall back to static image
    if os.path.exists('logo.mp4'):
        st.video('logo.mp4')
    elif os.path.exists('logo.gif'):
        st.image('logo.gif', width=400)
    elif os.path.exists('logo.png'):
        st.image('logo.png', width=400)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("# DOUBLEBARREL.QUEST")st.markdown(
    '<p class="subtitle">• Ultra-Safe Duplicate Remover • Complete Audit Trail •</p>',
    unsafe_allow_html=True
)

# Main container
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    
    st.markdown("### 📤 Upload Your Data")
    st.markdown("**Supports:** CSV, Excel (.xlsx, .xls)")
    
    uploaded_file = st.file_uploader(
        "",
        type=["csv", "xlsx", "xls"],
        help="Drop your file here or click to browse"
    )
    
    if uploaded_file is not None:
        try:
            # Read the file
            with st.spinner('🔵 Loading your data...'):
                if uploaded_file.name.endswith('.csv'):
                    try:
                        df_original = pd.read_csv(uploaded_file, encoding='utf-8')
                    except:
                        df_original = pd.read_csv(uploaded_file, encoding='ISO-8859-1')
                else:
                    df_original = pd.read_excel(uploaded_file)
            
            st.success(f"✅ **Loaded:** {uploaded_file.name}")
            st.info(f"📊 **Rows:** {len(df_original):,} | **Columns:** {len(df_original.columns)}")
            
            # Show preview
            with st.expander("👁️ Preview Data (first 5 rows)"):
                st.dataframe(df_original.head(), use_container_width=True)
            
            # Process duplicates
            with st.spinner('🔍 Scanning for duplicates...'):
                duplicate_mask = df_original.duplicated(keep='first')
                num_duplicates = duplicate_mask.sum()
            
            if num_duplicates == 0:
                st.success("🎉 **Perfect!** No duplicates found. Your data is clean!")
            else:
                st.warning(f"⚠️ **Found {num_duplicates:,} duplicates** ({(num_duplicates/len(df_original)*100):.1f}% of your data)")
                
                # Create clean dataset
                df_clean = df_original.drop_duplicates(keep='first')
                df_duplicates = df_original[duplicate_mask]
                
                # Verification
                verification_passed = (len(df_original) - num_duplicates == len(df_clean))
                
                if verification_passed:
                    st.success(f"✅ **Verified:** {len(df_original):,} - {num_duplicates:,} = {len(df_clean):,}")
                else:
                    st.error("❌ Math doesn't match! Please try again.")
                
                # Show results with brand colors
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.metric("Original Rows", f"{len(df_original):,}")
                    st.metric("Removed", f"{num_duplicates:,}")
                
                with col_b:
                    st.metric("Clean Rows", f"{len(df_clean):,}")
                    st.metric("Retained", f"{(len(df_clean)/len(df_original)*100):.1f}%")
                
                st.markdown("---")
                st.markdown("### 🎯 Download Results")
                
                col1, col2 = st.columns(2)
                
                # Prepare downloads
                with col1:
                    clean_csv = df_clean.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Clean Data",
                        data=clean_csv,
                        file_name=f"CLEAN_{uploaded_file.name.replace('.xlsx', '.csv').replace('.xls', '.csv')}",
                        mime="text/csv",
                        use_container_width=True,
                        type="primary"
                    )
                
                with col2:
                    duplicates_csv = df_duplicates.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📋 Duplicate Log",
                        data=duplicates_csv,
                        file_name=f"DUPLICATES_{uploaded_file.name.replace('.xlsx', '.csv').replace('.xls', '.csv')}",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # Preview clean data
                with st.expander("👁️ Preview Clean Data (first 10 rows)"):
                    st.dataframe(df_clean.head(10), use_container_width=True)
        
        except Exception as e:
            st.error(f"❌ **Error:** {str(e)}")
            st.info("Please ensure your file is a valid CSV or Excel format.")
    
    else:
        st.info("👆 **Drag & drop** your file above to get started")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; opacity: 0.8;">'
    '🔒 Secure • 🎨 Professional • ⚡ Fast • 🆓 100% Free<br>'
    '<strong>DoubleBarrel.Quest</strong> - Your trusted data cleanup tool'
    '</p>',
    unsafe_allow_html=True
)
