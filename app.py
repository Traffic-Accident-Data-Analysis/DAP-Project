import streamlit as st
import pandas as pd
import plotly.express as px

# ================= 1. CẤU HÌNH WEB =================
st.set_page_config(page_title="US Accidents Dashboard", layout="wide")

# ================= 2. LOAD DỮ LIỆU =================
@st.cache_data
def load_data():
    # Vì file của bạn đã có sẵn Year, Hour, Weekday... nên chỉ cần đọc file là xong!
    try:
        df = pd.read_csv('output/dashboard_data.csv') 
    except FileNotFoundError:
        try:
            # Dự phòng trường hợp bạn để file bên ngoài
            df = pd.read_csv('dashboard_data.csv')
        except FileNotFoundError:
            st.error("❌ Không tìm thấy file dữ liệu. Hãy kiểm tra lại!")
            st.stop()
    return df

df = load_data()

# ================= 3. SIDEBAR (BỘ LỌC) =================
st.sidebar.title("🚥 Điều khiển")

# Lọc Năm
years = sorted(df['Year'].dropna().unique(), reverse=True)
year = st.sidebar.selectbox("Chọn Năm", years)

# Lọc Bang
states = sorted(df['State'].dropna().unique())
state = st.sidebar.selectbox("Chọn Bang", states)

# Lọc Mức độ
severity_options = sorted(df['Severity'].dropna().unique())
severity = st.sidebar.selectbox("Mức độ nghiêm trọng", severity_options)

# ================= 4. XỬ LÝ LỌC DATA =================
filtered = df[
    (df["Year"] == year) &
    (df["State"] == state) &
    (df["Severity"] == severity)
]

st.title(f"Báo cáo Tai nạn tại {state} ({int(year)}) - Mức độ {severity}")

if len(filtered) == 0:
    st.warning("Không có dữ liệu cho bộ lọc này. Vui lòng chọn lại!")
    st.stop()

# ================= 5. KPIs =================
st.subheader("===== KPIs =====")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Tổng số vụ", f"{len(filtered):,}")
c2.metric("Số vụ mức 4", f"{len(filtered[filtered['Severity']==4]):,}")
c3.metric("Distance TB (mi)", f"{round(filtered['Distance(mi)'].mean(), 2)}")
c4.metric("Duration TB (phút)", f"{round(filtered['Duration'].mean(), 2)}")

# ================= 6. HEATMAP (BẢN ĐỒ NHIỆT) =================
st.subheader("===== Density Map (Bản đồ nhiệt) =====")

map_agg = filtered.groupby(
    [filtered['Start_Lat'].round(2), filtered['Start_Lng'].round(2)]
).size().reset_index(name='Count')

fig_map = px.density_mapbox(
    map_agg, lat="Start_Lat", lon="Start_Lng", z="Count",
    radius=8, zoom=4, mapbox_style="carto-positron",
    color_continuous_scale="Reds"
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
st.plotly_chart(fig_map, use_container_width=True)

# ================= 7. THỐNG KÊ THỜI GIAN =================
col_hour, col_week = st.columns(2)

with col_hour:
    st.subheader("===== Tai nạn theo giờ =====")
    hourly = filtered.groupby("Hour").size().reset_index(name="Count")
    fig_hour = px.line(hourly, x="Hour", y="Count", markers=True)
    st.plotly_chart(fig_hour, use_container_width=True)

with col_week:
    st.subheader("===== Tai nạn theo ngày trong tuần =====")
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday = filtered.groupby("Weekday").size().reindex(days_order).reset_index(name="Count")
    fig_week = px.bar(weekday, x="Weekday", y="Count", color="Count")
    st.plotly_chart(fig_week, use_container_width=True)

st.subheader("===== Heatmap Day vs Hour =====")
pivot = filtered.pivot_table(
    index="Weekday", columns="Hour", aggfunc="size", fill_value=0
).reindex(days_order)
fig_heat = px.imshow(pivot, aspect="auto", color_continuous_scale="Viridis")
st.plotly_chart(fig_heat, use_container_width=True)

# ================= 8. THỜI TIẾT & HẠ TẦNG =================
col_weather, col_infra = st.columns(2)

with col_weather:
    st.subheader("===== Thời tiết =====")
    weather = filtered["Weather_Condition"].value_counts().nlargest(10)
    fig_weather = px.pie(names=weather.index, values=weather.values, hole=0.3)
    st.plotly_chart(fig_weather, use_container_width=True)

with col_infra:
    st.subheader("===== Hạ tầng =====")
    infra_cols = ["Traffic_Signal", "Junction"]
    infra_data = []
    for col in infra_cols:
        if col in filtered.columns:
            count = filtered[filtered[col] == True].shape[0]
            infra_data.append([col, count])
    
    if infra_data:
        infra_df = pd.DataFrame(infra_data, columns=["Type","Count"])
        fig_infra = px.bar(infra_df, x="Count", y="Type", orientation="h", color="Type")
        st.plotly_chart(fig_infra, use_container_width=True)