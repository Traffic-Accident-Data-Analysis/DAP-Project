import pandas as pd
import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.express as px

# =========================================
# 1️⃣ LOAD DATA (KHỚP 100% VỚI DATA THỰC TẾ)
# =========================================

file_path = r"C:\Users\Admin\Desktop\DAP_Project\output\dashboard_data.csv"

# Các cột lấy trực tiếp từ file của bạn
cols_to_keep = [
    'Severity', 'Start_Lat', 'Start_Lng', 'City',
    'Temperature(F)', 'Weather_Condition',
    'Junction', 'Traffic_Signal', 'Sunrise_Sunset',
    'Hour', 'Month', 'Year', 'Weekday'
]

chunksize = 300000
sample_data = []

print("⏳ Loading dataset...")

for chunk in pd.read_csv(file_path, usecols=cols_to_keep, chunksize=chunksize):
    sample_data.append(chunk.sample(frac=0.015, random_state=42))

df_sample = pd.concat(sample_data, ignore_index=True)
df_sample = df_sample.dropna(subset=['Start_Lat', 'Start_Lng', 'Year', 'Month', 'Hour'])

# Reset index để tạo ID liền mạch
df_sample = df_sample.reset_index(drop=True)
df_sample["Accident_ID"] = df_sample.index.astype(int)

# Đảm bảo các cột thời gian là số nguyên
df_sample['Year'] = df_sample['Year'].astype(int)
df_sample['Month'] = df_sample['Month'].astype(int)
df_sample['Hour'] = df_sample['Hour'].astype(int)

# Dịch số Weekday (0-6) sang Tên thứ trong tuần
day_mapping = {
    0.0: 'Monday', 1.0: 'Tuesday', 2.0: 'Wednesday', 
    3.0: 'Thursday', 4.0: 'Friday', 5.0: 'Saturday', 6.0: 'Sunday'
}
df_sample['Day_of_Week'] = df_sample['Weekday'].map(day_mapping)
df_sample['Year_Month'] = df_sample['Year'].astype(str) + '-' + df_sample['Month'].astype(str).str.zfill(2)

available_years = sorted(df_sample["Year"].dropna().unique())

print("✅ Data Ready")

# =========================================
# 2️⃣ DASH APP
# =========================================

app = dash.Dash(__name__)
app.title = "US Accidents Professional Dashboard"

px.defaults.template = "plotly_dark"
px.defaults.color_continuous_scale = px.colors.sequential.Plasma

CARD_STYLE = {
    "backgroundColor": "#1f2630",
    "padding": "15px",
    "borderRadius": "12px",
    "boxShadow": "0px 4px 15px rgba(0,0,0,0.4)"
}

app.layout = html.Div([

    html.H1("US Accidents Dashboard",
            style={'textAlign':'center','marginBottom':'20px'}),

    # ================= MAP SECTION =================
    html.Div([
        html.H3("Accident Map"),

        dcc.RadioItems(
            id='map-type',
            options=[
                {'label': ' Scatter Map', 'value': 'scatter'},
                {'label': ' Heatmap', 'value': 'heat'}
            ],
            value='scatter',
            inline=True,
            style={'marginBottom':'10px'}
        ),

        dcc.Graph(
            id='map-graph',
            config={'scrollZoom': True, 'doubleClick': 'reset'},
            style={"height":"600px"}
        ),

        html.Div([
            dcc.Dropdown(
                id='year-filter',
                options=[{'label': str(y), 'value': y} for y in available_years],
                placeholder="Select Year",
                style={'width':'200px', 'color':'black'}
            ),

            html.Button(
                "Reset Filters",
                id="reset-btn",
                style={
                    'padding':'8px 18px',
                    'backgroundColor':'#ff4d4f',
                    'color':'white',
                    'border':'none',
                    'borderRadius':'8px',
                    'cursor':'pointer'
                }
            )
        ], style={'display':'flex','gap':'15px','marginTop':'10px'})

    ], style=CARD_STYLE),

    html.Br(),

    # ================= FILTER =================
    html.Div([
        html.Label("Filter by Severity"),
        dcc.Dropdown(
            id='severity-filter',
            options=[{'label': str(s), 'value': s}
                     for s in sorted(df_sample['Severity'].unique())],
            multi=True,
            style={'color':'black'}
        )
    ], style={**CARD_STYLE, "width":"40%","margin":"auto"}),

    html.Br(),

    # ================= CHART GRID =================
    html.Div([
        html.Div(dcc.Graph(id='time-trend-graph'), style={"gridColumn": "1 / -1", **CARD_STYLE}), 

        html.Div(dcc.Graph(id='day-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='hour-sun-graph'), style=CARD_STYLE), 
        
        html.Div(dcc.Graph(id='weather-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='severity-graph'), style=CARD_STYLE),
        
        html.Div(dcc.Graph(id='city-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='infra-graph'), style=CARD_STYLE),

    ], style={
        "display":"grid",
        "gridTemplateColumns":"1fr 1fr",
        "gap":"20px"
    }),

], style={
    "backgroundColor":"#0a0f18", 
    "padding":"20px",
    "color":"white"
})

# =========================================
# 3️⃣ CALLBACK
# =========================================

@app.callback(
    [
        Output('time-trend-graph', 'figure'),
        Output('day-graph', 'figure'),
        Output('hour-sun-graph', 'figure'),
        Output('weather-graph', 'figure'),
        Output('severity-graph', 'figure'),
        Output('city-graph', 'figure'),
        Output('infra-graph', 'figure'),
        Output('map-graph', 'figure'),
    ],
    [
        Input('weather-graph', 'clickData'),
        Input('infra-graph', 'clickData'),
        Input('map-graph', 'clickData'),
        Input('severity-filter', 'value'),
        Input('map-type', 'value'),
        Input('reset-btn', 'n_clicks'),
        Input('year-filter', 'value')
    ]
)
def update_dashboard(weather_click, infra_click, map_click,
                     severity_filter, map_type, reset_click, year_filter):

    try:
        ctx = callback_context
        triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        filtered = df_sample.copy()

        if triggered != "reset-btn":
            if year_filter:
                filtered = filtered[filtered["Year"] == year_filter]

            if severity_filter:
                filtered = filtered[filtered['Severity'].isin(severity_filter)]

            if weather_click and triggered == 'weather-graph':
                filtered = filtered[filtered['Weather_Condition'] == weather_click['points'][0]['x']]

            if infra_click and triggered == 'infra-graph':
                selected_type = infra_click['points'][0]['x']
                filtered = filtered[filtered[selected_type] == True]

            # ===== LOGIC BẮT CLICK BẢN ĐỒ (ĐÃ FIX CHUẨN) =====
            if map_click and triggered == "map-graph":
                point_data = map_click['points'][0]
                custom_data = point_data.get('customdata')
                
                if custom_data is not None:
                    # Plotly lưu custom_data ở index 0, hover_data theo sau. 
                    # Ép kiểu int để so sánh chính xác với cột Accident_ID dạng int
                    accident_id = int(custom_data[0]) 
                    filtered = filtered[filtered['Accident_ID'] == accident_id]

        if filtered.empty:
            filtered = df_sample.copy()

        # ===== 1. Xu Hướng Theo Thời Gian =====
        trend_df = filtered.groupby('Year_Month').size().reset_index(name='Count')
        trend_df = trend_df.sort_values('Year_Month')
        fig_trend = px.line(trend_df, x='Year_Month', y='Count',
                            title="Accidents Trend Over Time",
                            markers=True)
        fig_trend.update_xaxes(type='category', tickangle=45) 

        # ===== 2. Thứ trong tuần =====
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_df = filtered['Day_of_Week'].value_counts().reindex(days_order).reset_index()
        day_df.columns = ['Day_of_Week', 'Count']
        fig_day = px.bar(day_df, x='Day_of_Week', y='Count', 
                         title="Accidents by Day of Week", 
                         color='Count', color_continuous_scale='Plasma')

        # ===== 3. Giờ trong ngày vs Day/Night =====
        fig_hour_sun = px.histogram(filtered, x='Hour', color='Sunrise_Sunset', nbins=24,
                                    title="Accidents by 24h & Day/Night Phase",
                                    barmode='stack', 
                                    color_discrete_map={'Day': '#F39C12', 'Night': '#34495E'}) 
        fig_hour_sun.update_xaxes(dtick=1) 

        # ===== 4. Các biểu đồ khác =====
        fig_sev = px.histogram(filtered, x='Severity', color='Severity', title="Severity Distribution")

        fig_city = px.histogram(filtered, x='City', title="Top Cities")
        fig_city.update_xaxes(categoryorder='total descending', range=[-.5, 19.5]) 

        fig_weather = px.histogram(filtered, x='Weather_Condition', title="Weather Conditions").update_xaxes(categoryorder='total descending', range=[-.5, 14.5])

        infra_df = pd.DataFrame({
            "Type": ["Junction", "Traffic_Signal"],
            "Count": [
                filtered['Junction'].fillna(False).sum(),
                filtered['Traffic_Signal'].fillna(False).sum()
            ]
        })
        fig_infra = px.bar(infra_df, x='Type', y='Count', title="Infrastructure Analysis")

        # ===== 5. MAP =====
        map_data = filtered
        if len(map_data) > 50000:
            map_data = map_data.sample(50000, random_state=42)
            
        center_us = dict(lat=39.8283, lon=-98.5795)
        
        if map_type == 'scatter':
            fig_map = px.scatter_map(
                map_data, lat="Start_Lat", lon="Start_Lng",
                color="Severity", hover_name="City", hover_data=["Weather_Condition"], custom_data=["Accident_ID"],
                height=600, map_style="open-street-map", center=center_us 
            )
        else:
            fig_map = px.density_map(
                map_data, lat='Start_Lat', lon='Start_Lng', z='Severity',
                radius=6, height=600, map_style="open-street-map", center=center_us 
            )
            
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, uirevision="map")

        return (
            fig_trend, fig_day, fig_hour_sun, fig_weather,
            fig_sev, fig_city, fig_infra, fig_map
        )

    except Exception as e:
        print("🔥 CALLBACK ERROR:", e)
        empty_fig = px.scatter(title="Error")
        return (empty_fig,) * 8

# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    app.run(debug=True)