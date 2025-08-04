import streamlit as st
import pandas as pd
import requests
import io
import re

# Secure Dropbox URL from secrets
DROPBOX_URL = st.secrets["DROPBOX_URL"]

@st.cache_data
def load_data():
    try:
        response = requests.get(DROPBOX_URL)
        response.raise_for_status()
        return pd.read_pickle(io.BytesIO(response.content))
    except Exception as e:
        st.error(f"Failed to load data from Dropbox: {e}")
        return None

def search_rsid(df, query_string):
    queries = [q.strip().lower() for q in query_string.split(',') if q.strip()]
    return df[df['rsid'].str.lower().fillna('').isin(queries)]

def keyword_search(df, query):
    query = query.lower()
    text_columns = df.select_dtypes(include=['object']).columns
    mask = pd.Series(False, index=df.index)
    for col in text_columns:
        try:
            col_mask = df[col].astype(str).str.lower().str.contains(query, na=False)
            mask = mask | col_mask
        except Exception as e:
            st.warning(f"Skipped column '{col}' due to error: {e}")
    return df[mask]

def highlight_matches_styler(df, query):
    query_lower = query.lower()
    def highlight(val):
        if isinstance(val, str) and query_lower in val.lower():
            return "background-color: yellow"
        return ""
    return df.head(100).style.applymap(highlight)

# --- UI ---
st.title("CuraSNP: Your Curated SNP Explorer")

search_input = st.text_input("Enter RSID(s) (e.g., rs123, rs456) or Keyword:", "").strip()

if search_input:
    with st.spinner("Loading data and searching..."):
        df = load_data()
        if df is None:
            st.error("Data could not be loaded.")
        else:
            if search_input.lower().startswith("rs") and 'rsid' in df.columns:
                results = search_rsid(df, search_input)
            else:
                results = keyword_search(df, search_input)

            if results.empty:
                st.error("No matching records found.")
            else:
                st.success(f"Found {len(results)} matching record(s).")
                styled_df = highlight_matches_styler(results, search_input)
                st.dataframe(styled_df, use_container_width=True)

                if len(results) > 100:
                    st.warning("Only showing first 100 records. Refine your search for more specific results.")

                csv = results.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results as CSV", data=csv, file_name="snp_results.csv", mime='text/csv')
