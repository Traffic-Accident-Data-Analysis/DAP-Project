import pandas as pd
import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.express as px

# =========================================
# 1. LOAD DATA (TỐI ƯU HÓA & QUY ĐỔI ĐẠI LƯỢNG)
# =========================================

file_path = r"D:\FPT\Spring 2026\DAP391m\DAP-Project\output\dashboard_data.csv"

cols_to_keep = [
    'Severity', 'Start_Lat', 'Start_Lng', 'Distance(mi)', 'City', 'State',
    'Temperature(F)', 'Humidity(%)', 'Visibility(mi)', 'Precipitation(in)',
    'Weather_Condition', 'Junction', 'Traffic_Signal', 'Sunrise_Sunset',
    'Hour', 'Day', 'Month', 'Year', 'Weekday', 'Duration'
]

dtypes_optimized = {
    'Severity': 'int8',
    'Start_Lat': 'float32',
    'Start_Lng': 'float32',
    'Distance(mi)': 'float32',
    'City': 'category',
    'State': 'category',
    'Temperature(F)': 'float32',
    'Humidity(%)': 'float32',
    'Visibility(mi)': 'float32',
    'Precipitation(in)': 'float32',
    'Weather_Condition': 'category',
    'Sunrise_Sunset': 'category',
    'Duration': 'float32'
}

chunksize = 500000
data_chunks = []

print("⏳ Loading full dataset (7.7 million rows)... Please wait.")

for chunk in pd.read_csv(file_path, usecols=cols_to_keep, dtype=dtypes_optimized, chunksize=chunksize):
    # Quy đổi đại lượng
    if 'Temperature(F)' in chunk.columns:
        chunk['Temperature(C)'] = (chunk['Temperature(F)'] - 32) * 5.0 / 9.0
        chunk = chunk.drop(columns=['Temperature(F)'])
    if 'Distance(mi)' in chunk.columns:
        chunk['Distance(km)'] = chunk['Distance(mi)'] * 1.60934
        chunk = chunk.drop(columns=['Distance(mi)'])
    if 'Visibility(mi)' in chunk.columns:
        chunk['Visibility(km)'] = chunk['Visibility(mi)'] * 1.60934
        chunk = chunk.drop(columns=['Visibility(mi)'])
    if 'Precipitation(in)' in chunk.columns:
        chunk['Precipitation(mm)'] = chunk['Precipitation(in)'] * 25.4
        chunk = chunk.drop(columns=['Precipitation(in)'])
    
    data_chunks.append(chunk)

df_full = pd.concat(data_chunks, ignore_index=True)

# Làm sạch dữ liệu cơ bản
df_full = df_full.dropna(subset=['Start_Lat', 'Start_Lng', 'Year', 'Month', 'Day', 'Hour', 'City'])
df_full = df_full.reset_index(drop=True)
df_full["Accident_ID"] = df_full.index.astype(int)

# Ép kiểu dữ liệu
df_full['Year'] = df_full['Year'].astype('int16')
df_full['Month'] = df_full['Month'].astype('int8')
df_full['Day'] = df_full['Day'].astype('int8')
df_full['Hour'] = df_full['Hour'].astype('int8')
df_full['Weekday'] = df_full['Weekday'].astype('int8')
df_full['Junction'] = df_full['Junction'].fillna(False).astype(bool)
df_full['Traffic_Signal'] = df_full['Traffic_Signal'].fillna(False).astype(bool)

day_mapping = {
    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 
    3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'
}
df_full['Day_of_Week'] = df_full['Weekday'].map(day_mapping).astype('category')
df_full['Year_Month'] = df_full['Year'].astype(str) + '-' + df_full['Month'].astype(str).str.zfill(2)
df_full['Year_Month'] = df_full['Year_Month'].astype('category')

available_years = sorted(df_full["Year"].unique())

print(f"✅ Data Ready: Loaded {len(df_full):,} rows successfully!")

# =========================================
# 2. DASH APP LAYOUT
# =========================================

app = dash.Dash(__name__)
app.title = "US Accidents Dashboard"

px.defaults.template = "plotly_dark"
px.defaults.color_continuous_scale = px.colors.sequential.Plasma

CARD_STYLE = {
    "backgroundColor": "#1f2630",
    "padding": "15px",
    "borderRadius": "12px",
    "boxShadow": "0px 4px 15px rgba(0,0,0,0.4)"
}

app.layout = html.Div([

    html.H1("US Accidents Dashboard", style={'textAlign':'center','marginBottom':'20px'}),

    # --- MAP 1: TỌA ĐỘ CHI TIẾT ---
    html.Div([
        html.H3("Accident Map"),
        dcc.RadioItems(
            id='map-type',
            options=[{'label': ' Scatter Map', 'value': 'scatter'}, {'label': ' Heatmap', 'value': 'heat'}],
            value='scatter', inline=True, style={'marginBottom':'10px'}
        ),
        dcc.Graph(id='map-graph', config={'scrollZoom': True}, style={"height":"550px", "marginBottom":"10px"}),
        html.Div([
            dcc.Dropdown(id='year-filter', options=[{'label': str(y), 'value': y} for y in available_years],
                         placeholder="Select Year", style={'width':'200px', 'color':'black'}),
            html.Button("Reset Filters", id="reset-btn", style={
                'padding':'8px 18px', 'backgroundColor':'#ff4d4f', 'color':'white',
                'border':'none', 'borderRadius':'8px', 'cursor':'pointer'
            })
        ], style={'display':'flex','gap':'15px'})
    ], style={**CARD_STYLE, "marginBottom": "20px"}),

    # --- MAP 2: BẢN ĐỒ THÀNH PHỐ  ---
    html.Div([
        html.H3("City Aggregated Map"),
        dcc.Graph(id='map-graph-2', config={'scrollZoom': True}, style={"height":"600px", "marginBottom":"10px"}),
        html.Div([
            dcc.Dropdown(id='year-filter-2', options=[{'label': str(y), 'value': y} for y in available_years],
                         placeholder="Select Year", style={'width':'200px', 'color':'black'}),
            html.Button("Reset Map 2", id="reset-btn-2", style={
                'padding':'8px 18px', 'backgroundColor':'#3498DB', 'color':'white',
                'border':'none', 'borderRadius':'8px', 'cursor':'pointer'
            })
        ], style={'display':'flex','gap':'15px'})
    ], style={**CARD_STYLE, "marginBottom": "20px"}),

    # --- BỘ LỌC CHUNG CHO CHARTS ---
    html.Div([
        html.Label("Severity"),
        dcc.Dropdown(
            id='severity-filter',
            options=[{'label': f"Severity {s}", 'value': s} for s in sorted(df_full['Severity'].unique())],
            multi=True, style={'color':'black'}
        )
    ], style={**CARD_STYLE, "width":"40%", "margin":"auto", "marginBottom": "20px"}),

    # --- LƯỚI BIỂU ĐỒ ---
    html.Div([
        html.Div(dcc.Graph(id='time-trend-graph'), style={"gridColumn": "1 / -1", **CARD_STYLE}), 
        html.Div(dcc.Graph(id='day-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='day-month-graph'), style=CARD_STYLE), 
        html.Div(dcc.Graph(id='hour-sun-graph'), style=CARD_STYLE), 
        html.Div(dcc.Graph(id='duration-graph'), style=CARD_STYLE),  
        html.Div(dcc.Graph(id='weather-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='severity-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='city-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='infra-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='humidity-graph'), style=CARD_STYLE),  
        html.Div(dcc.Graph(id='visibility-graph'), style=CARD_STYLE),
        html.Div(dcc.Graph(id='precip-graph'), style={"gridColumn": "1 / -1", **CARD_STYLE}), 
    ], style={"display":"grid", "gridTemplateColumns":"1fr 1fr", "gap":"20px"}),

], style={"backgroundColor":"#4174AB", "padding":"20px", "color":"white"})

# =========================================
# 3. CALLBACKS
# =========================================

@app.callback(Output('year-filter', 'value'), Input('reset-btn', 'n_clicks'), prevent_initial_call=True)
def reset_map1_year(n): return None

@app.callback(Output('year-filter-2', 'value'), Input('reset-btn-2', 'n_clicks'), prevent_initial_call=True)
def reset_map2_year(n): return None

@app.callback(Output('map-graph-2', 'figure'), Input('year-filter-2', 'value'))
def update_aggregated_map(year_filter_2):
    filtered_2 = df_full.copy()
    if year_filter_2:
        filtered_2 = filtered_2[filtered_2['Year'] == year_filter_2]

    city_agg = filtered_2.groupby('City', observed=True).agg(
        Total_Accidents=('Severity', 'size'),
        Avg_Severity=('Severity', 'mean'),
        Lat=('Start_Lat', 'mean'), Lng=('Start_Lng', 'mean')
    ).reset_index()
    city_agg = city_agg[city_agg['Total_Accidents'] > 0]

    fig_map2 = px.scatter_map(
        city_agg, lat="Lat", lon="Lng", size="Total_Accidents", color="Avg_Severity",
        hover_name="City", hover_data={"Total_Accidents": ":,", "Avg_Severity": ":.2f", "Lat": False, "Lng": False},
        size_max=50, opacity=0.7, color_continuous_scale="Reds", height=600, 
        map_style="open-street-map", center=dict(lat=39.8283, lon=-98.5795)
    )
    fig_map2.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, uirevision="map2")
    return fig_map2

@app.callback(
    [
        Output('map-graph', 'figure'), Output('time-trend-graph', 'figure'), 
        Output('day-graph', 'figure'), Output('day-month-graph', 'figure'), 
        Output('hour-sun-graph', 'figure'), Output('duration-graph', 'figure'), 
        Output('weather-graph', 'figure'), Output('severity-graph', 'figure'), 
        Output('city-graph', 'figure'), Output('infra-graph', 'figure'), 
        Output('humidity-graph', 'figure'), Output('visibility-graph', 'figure'), 
        Output('precip-graph', 'figure')
    ],
    [
        Input('map-type', 'value'), Input('year-filter', 'value'), Input('severity-filter', 'value'),
        # Bắt sự kiện Click từ TẤT CẢ các biểu đồ
        Input('map-graph', 'clickData'), Input('weather-graph', 'clickData'), 
        Input('infra-graph', 'clickData'), Input('city-graph', 'clickData'),
        Input('day-graph', 'clickData'), Input('day-month-graph', 'clickData'),
        Input('time-trend-graph', 'clickData'), Input('severity-graph', 'clickData')
    ]
)
def update_dashboard(map_type, year_filter, severity_filter, 
                     map_click, weather_click, infra_click, city_click, 
                     day_click, day_month_click, trend_click, sev_click):
    try:
        ctx = callback_context
        triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        filtered = df_full.copy()

        # Áp dụng bộ lọc Dropdown
        if year_filter: 
            filtered = filtered[filtered["Year"] == year_filter]
        if severity_filter: 
            filtered = filtered[filtered['Severity'].isin(severity_filter)]
            
        # Áp dụng bộ lọc theo Cú Click (Cross-filtering)
        if triggered == 'weather-graph' and weather_click:
            filtered = filtered[filtered['Weather_Condition'] == weather_click['points'][0]['x']]
            
        elif triggered == 'infra-graph' and infra_click:
            selected_type = infra_click['points'][0]['x']
            filtered = filtered[filtered[selected_type] == True]
            
        elif triggered == 'city-graph' and city_click:
            filtered = filtered[filtered['City'] == city_click['points'][0]['x']]
            
        elif triggered == 'day-graph' and day_click:
            filtered = filtered[filtered['Day_of_Week'] == day_click['points'][0]['x']]
            
        elif triggered == 'day-month-graph' and day_month_click:
            filtered = filtered[filtered['Day'] == day_month_click['points'][0]['x']]
            
        elif triggered == 'time-trend-graph' and trend_click:
            filtered = filtered[filtered['Year_Month'] == trend_click['points'][0]['x']]
            
        elif triggered == 'severity-graph' and sev_click:
            filtered = filtered[filtered['Severity'] == sev_click['points'][0]['x']]
            
        elif triggered == "map-graph" and map_click:
            custom_data = map_click['points'][0].get('customdata')
            if custom_data is not None:
                filtered = filtered[filtered['Accident_ID'] == int(custom_data[0])]

        if filtered.empty: 
            filtered = df_full.copy()

        # --- BIỂU ĐỒ XU HƯỚNG THỜI GIAN ---
        trend_df = filtered.groupby('Year_Month', observed=True).size().reset_index(name='Count')
        trend_df = trend_df.sort_values('Year_Month')
        fig_trend = px.line(trend_df, x='Year_Month', y='Count', title="Accidents Trend", markers=True)
        fig_trend.update_xaxes(type='category', tickangle=45)

        # --- CÁC BIỂU ĐỒ CÒN LẠI ---
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_df = filtered['Day_of_Week'].value_counts().reindex(days_order).reset_index()
        day_df.columns = ['Day_of_Week', 'Count']
        fig_day = px.bar(day_df, x='Day_of_Week', y='Count', title="Accidents by Day of Week", color='Count')

        fig_hour_sun = px.histogram(filtered, x='Hour', color='Sunrise_Sunset', nbins=24, title="Accidents by Day/Night", barmode='stack').update_xaxes(dtick=1) 
        fig_sev = px.histogram(filtered, x='Severity', color='Severity', title="Severity Distribution")
        
        top_cities = filtered['City'].value_counts().nlargest(20).index
        fig_city = px.histogram(filtered[filtered['City'].isin(top_cities)], x='City', title="Top Cities").update_xaxes(categoryorder='total descending') 

        top_weather = filtered['Weather_Condition'].value_counts().nlargest(15).index
        fig_weather = px.histogram(filtered[filtered['Weather_Condition'].isin(top_weather)], x='Weather_Condition', title="Top Weather Conditions").update_xaxes(categoryorder='total descending')

        fig_infra = px.bar(pd.DataFrame({"Type": ["Junction", "Traffic_Signal"], "Count": [filtered['Junction'].sum(), filtered['Traffic_Signal'].sum()]}), x='Type', y='Count', title="Infrastructure Analysis")

        day_m_df = filtered['Day'].value_counts().sort_index().reset_index()
        day_m_df.columns = ['Day_of_Month', 'Count']
        fig_day_month = px.bar(day_m_df, x='Day_of_Month', y='Count', title="Accidents by Day of Month", color='Count').update_xaxes(dtick=1)

        dur_filtered = filtered[filtered['Duration'] <= 1440]
        fig_duration = px.histogram(dur_filtered, x='Duration', nbins=30, title="Duration Distribution (Minutes)")

        fig_humidity = px.histogram(filtered, x='Humidity(%)', nbins=20, title="Humidity (%)")
        fig_visibility = px.histogram(filtered, x='Visibility(km)', nbins=20, title="Visibility (km)", log_y=True)
        
        rain_filtered = filtered[filtered['Precipitation(mm)'] > 0]
        fig_precip = px.histogram(rain_filtered, x='Precipitation(mm)', nbins=30, title="Precipitation", log_y=True)

        # --- MAP 1 ---
        map_data = filtered.sample(50000, random_state=42) if len(filtered) > 50000 else filtered
        center_us = dict(lat=39.8283, lon=-98.5795)
        
        if map_type == 'scatter':
            fig_map1 = px.scatter_map(map_data, lat="Start_Lat", lon="Start_Lng", color="Severity", hover_name="City", hover_data={"Weather_Condition": True, "Temperature(C)": ":.1f", "Distance(km)": ":.2f"}, custom_data=["Accident_ID"], height=550, map_style="open-street-map", center=center_us)
        else:
            fig_map1 = px.density_map(map_data, lat='Start_Lat', lon='Start_Lng', z='Severity', radius=6, height=550, map_style="open-street-map", center=center_us)
        fig_map1.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, uirevision="map1")

        return fig_map1, fig_trend, fig_day, fig_day_month, fig_hour_sun, fig_duration, fig_weather, fig_sev, fig_city, fig_infra, fig_humidity, fig_visibility, fig_precip

    except Exception as e:
        print(" CALLBACK ERROR:", e)
        err = px.scatter(title="Error processing data")
        return (err,) * 13

if __name__ == "__main__":
    app.run(debug=True)