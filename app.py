import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Universal Data Analyzer", layout="wide")
st.title("📊 Universal Data Analysis Tool")

DB_PATH = "universal_data.db"

# 1. File Upload Section
st.sidebar.header("📂 Upload a Data File")
uploaded_file = st.sidebar.file_uploader("Choose a file (CSV, Excel, JSON, Parquet)", type=["csv", "xlsx", "xls", "json", "parquet"])

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1]
    if file_type in ["xlsx", "xls"]:
        df = pd.read_excel(uploaded_file)
    elif file_type == "json":
        df = pd.read_json(uploaded_file)
    elif file_type == "parquet":
        df = pd.read_parquet(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    st.subheader("Preview of Uploaded Data")
    st.dataframe(df.head())

    table_name = st.sidebar.text_input("Enter table name for DB:", value="my_table")

    if st.sidebar.button("📥 Load into Database"):
        conn = sqlite3.connect(DB_PATH)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()
        st.success(f"Table '{table_name}' loaded into {DB_PATH} ✅")

# 2. Table Explorer
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]

st.sidebar.header("🧭 Explore Tables")
selected_table = st.sidebar.selectbox("Choose a table", tables if tables else ["No tables yet"])

if selected_table != "No tables yet":
    df = pd.read_sql(f"SELECT * FROM {selected_table}", conn)
    st.subheader(f"🔎 Data from `{selected_table}`")
    st.dataframe(df)

    # KPI Summary
    st.markdown("### 📌 Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows", f"{len(df):,}")
    col2.metric("Null %", f"{df.isnull().mean().mean()*100:.2f}%")
    col3.metric("Unique Records", f"{df.drop_duplicates().shape[0]}")

    # Filtering
    st.markdown("### 🔍 Filter and Group")
    cols = df.columns.tolist()
    filter_column = st.selectbox("Column to filter by", options=cols)
    if pd.api.types.is_numeric_dtype(df[filter_column]):
        min_val, max_val = st.slider("Value range", float(df[filter_column].min()), float(df[filter_column].max()), (float(df[filter_column].min()), float(df[filter_column].max())))
        filtered_df = df[df[filter_column].between(min_val, max_val)]
    else:
        unique_vals = df[filter_column].dropna().unique().tolist()
        selected_vals = st.multiselect("Select values", unique_vals, default=unique_vals)
        filtered_df = df[df[filter_column].isin(selected_vals)]

    st.dataframe(filtered_df)

    # Grouping + Charts
    st.markdown("### 🧮 Group and Visualize")
    group_col = st.selectbox("Group by column", options=cols)
    agg_col = st.selectbox("Aggregate column", options=cols)
    agg_func = st.selectbox("Aggregation function", ["sum", "mean", "count", "max", "min"])

    if pd.api.types.is_numeric_dtype(df[agg_col]):
        grouped = filtered_df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
        st.write(grouped)

        chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Area", "Pie"])
        if chart_type == "Bar":
            st.bar_chart(grouped.set_index(group_col))
        elif chart_type == "Line":
            st.line_chart(grouped.set_index(group_col))
        elif chart_type == "Area":
            st.area_chart(grouped.set_index(group_col))
        elif chart_type == "Pie":
            fig = px.pie(grouped, names=group_col, values=agg_col)
            st.plotly_chart(fig)

    # Histogram
    st.markdown("### 📈 Value Distribution")
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    if numeric_cols:
        selected_col = st.selectbox("Column for Histogram", numeric_cols)
        fig = px.histogram(df, x=selected_col, nbins=30)
        st.plotly_chart(fig)

    # Correlation Heatmap
    st.markdown("### 📊 Correlation Heatmap")
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        fig, ax = plt.subplots()
        sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
        st.pyplot(fig)

    st.markdown("---")
    st.subheader("📤 Export Filtered Data")
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{selected_table}_filtered.csv",
        mime="text/csv",
    )

conn.close()
