import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# =============================
# 🎨 PAGE CONFIGURATION
# =============================
st.set_page_config(
    page_title="Job Market Explorer",
    page_icon="💼",
    layout="wide"
)

# =============================
# 💅 CUSTOM DARK THEME CSS
# =============================
st.markdown("""
<style>
    .stApp { background-color: #111111; }
    .main-header {
        font-size: 2.6rem; font-weight: 700; color: #329fc9;
        text-align: center; margin-bottom: 1.5rem;
    }
    .job-card {
        background-color: #1a1a1a; border: 1px solid #333333;
        border-radius: 15px; padding: 1.2rem; margin-bottom: 1rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        transition: all 0.25s ease-in-out;
        display: flex; justify-content: space-between; align-items: center;
    }
    .job-card:hover { border-color: crimson; transform: scale(1.01); }
    .job-title { font-size: 1.2rem; font-weight: 600; color: #ffffff; }
    .job-info { color: #cccccc; font-size: 0.9rem; }
    .salary { color: #329fc9; font-weight: 600; margin-top: 4px; }
    .apply-btn {
        background-color: crimson; color: white;
        padding: 0.4rem 1rem; border-radius: 8px;
        text-decoration: none; font-weight: bold;
    }
    .apply-btn:hover { background-color: #ff4d4d; }
    .section-header {
        color: crimson; font-size: 1.5rem;
        font-weight: 600; margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# ⚡️ LOAD & CACHE DATA
# =============================
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv('all_upwork_jobs_2024-02-07-2024-03-24.csv')

    # Basic cleaning
    df['country'].fillna('Unknown', inplace=True)
    df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
    df['hourly_low'] = pd.to_numeric(df.get('hourly_low', pd.Series()), errors='coerce')
    df['hourly_high'] = pd.to_numeric(df.get('hourly_high', pd.Series()), errors='coerce')
    df['budget'] = pd.to_numeric(df.get('budget', pd.Series()), errors='coerce')
    df['hourly_avg'] = (df['hourly_low'] + df['hourly_high']) / 2

    # Fast clean titles (vectorized)
    df['clean_title'] = (
        df['title']
        .fillna('')
        .str.lower()
        .str.replace(r'[^\w\s]', ' ', regex=True)
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )
    df['published_month'] = df['published_date'].dt.to_period('M').astype(str)
    return df


# =============================
# ⚙️ FAST FILTER FUNCTION
# =============================
def fast_filter(df, country, job_type, min_salary, search_remote, date_range, search_keyword):
    query_list = []

    if country != "All":
        query_list.append(f"country.str.contains(@country, case=False, na=False)")

    if job_type == "Hourly":
        query_list.append("hourly_avg.notna()")
    elif job_type == "Fixed / Permanent":
        query_list.append("budget.notna()")

    if min_salary > 0:
        query_list.append("hourly_avg >= @min_salary")

    if search_remote:
        query_list.append("clean_title.str.contains('remote', case=False, na=False)")

    if search_keyword.strip() != "":
        query_list.append("clean_title.str.contains(@search_keyword, case=False, na=False)")

    # Apply all filters in one go using pandas.query() for speed
    if query_list:
        query_str = " & ".join(query_list)
        df = df.query(query_str)

    # Apply date filter separately (since query() can't handle datetimes well)
    if date_range and len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df = df[(df['published_date'] >= start) & (df['published_date'] <= end)]

    return df


# =============================
# 🚀 MAIN FUNCTION
# =============================
def main():
    st.markdown('<div class="main-header">💼 Job Market Explorer</div>', unsafe_allow_html=True)
    df = load_data()

    # ======================
    # 🧭 Sidebar Filters
    # ======================
    st.sidebar.title("🔎 Job Filters")

    countries = ['All'] + sorted(df['country'].dropna().unique().tolist())
    country = st.sidebar.selectbox("🌍 Country", countries)
    job_type = st.sidebar.selectbox("💼 Job Type", ["All", "Hourly", "Fixed / Permanent"])
    min_salary = st.sidebar.slider("💰 Min Hourly Rate ($)", 0, 200, 20)
    search_remote = st.sidebar.checkbox("🌐 Remote Jobs Only")
    date_range = st.sidebar.date_input("📅 Published Date Range", [])
    search_keyword = st.sidebar.text_input("🔤 Search by Keyword", "")

    show_btn = st.sidebar.button("📥 Show Jobs")

    # ======================
    # 🧾 Display Jobs Section
    # ======================
    st.markdown('<div class="section-header">🔥 All Available Jobs</div>', unsafe_allow_html=True)

    # Show progress only during filtering
    if show_btn:
        with st.spinner("Filtering jobs..."):
            filtered_jobs = fast_filter(df, country, job_type, min_salary, search_remote, date_range, search_keyword)
    else:
        filtered_jobs = df.copy()

    st.write(f"Showing {len(filtered_jobs)} jobs based on filters:")

    # Display jobs
    if len(filtered_jobs) == 0:
        st.warning("No jobs found. Try adjusting filters.")
    else:
        # Limit visible jobs for faster render (you can increase if needed)
        for _, job in filtered_jobs.head(100).iterrows():
            job_link = f"https://www.upwork.com/jobs/{job['title'].replace(' ', '-')}"
            st.markdown(f"""
            <div class="job-card">
                <div>
                    <div class="job-title">{job['title']}</div>
                    <div class="job-info">
                        📍 {job['country']} &nbsp; | &nbsp; 📅 {job['published_date'].strftime('%Y-%m-%d')}
                    </div>
                    <div class="salary">
                        💵 {'$'+str(round(job['hourly_avg'],2))+'/hr' if pd.notna(job['hourly_avg']) else ('$'+str(job['budget'])+' budget')}
                    </div>
                </div>
                <a class="apply-btn" href="{job_link}" target="_blank">Apply 🔗</a>
            </div>
            """, unsafe_allow_html=True)

    # ======================
    # 📈 Market Trends
    # ======================
    st.markdown('<div class="section-header">📈 Job Market Trends</div>', unsafe_allow_html=True)
    trend_data = df.groupby('published_month').agg({'title': 'count', 'hourly_avg': 'mean'}).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.line(trend_data, x='published_month', y='title',
                       title='📊 Monthly Job Postings',
                       color_discrete_sequence=['crimson'])
        fig1.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='#ffffff')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.line(trend_data, x='published_month', y='hourly_avg',
                       title='💰 Average Hourly Rate Trend',
                       color_discrete_sequence=['#329fc9'])
        fig2.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='#ffffff')
        st.plotly_chart(fig2, use_container_width=True)


# =============================
# 🏁 RUN APP
# =============================
if __name__ == "__main__":
    main()
