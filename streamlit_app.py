import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
from calendar import monthrange
import plotly.express as px


def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")



st.markdown('<div class="custom-style">Welcome to the Historical Weather Data App!</div>', unsafe_allow_html=True)



st.title("Historical Weather Data 🌤")

st.write("Enter your API key from: [OpenWeatherMap](https://openweathermap.org/)")
api_key = st.text_input('API Key')

locations = {
    "BYUI": (43.815374637107645, -111.78322659522182),
    "BYU": (40.252817324377304, -111.64885969301183),
    "BYUH": (21.64211300311155, -157.92673597531686),
# "MIT": (42.360091, -71.094160),
# "Stanford": (37.427475, -122.169719), 
# "Harvard": (42.377003, -71.116660), 
# "Caltech": (34.137658, -118.125269), 
# "Princeton": (40.343989, -74.651448), 
}

df_locations = pd.DataFrame(locations.values(), index=locations.keys(), columns=['LATITUDE', 'LONGITUDE'])


st.map(df_locations)

selected_month = st.selectbox('Select Which Month', ('October', 'November', 'December', 'January', 'February', 'March'))

temp_threshold = st.slider(
    'Enter temperature threshold (°F):', 
    min_value=50,   
    max_value=100, 
    value=75       
)


months_to_numbers = {
    'January': 1, 'February': 2, 'March': 3,
    'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9,
    'October': 10, 'November': 11, 'December': 12,
}

current_year = datetime.now().year
current_month = datetime.now().month
selected_month_num = months_to_numbers[selected_month]

if selected_month_num > current_month:
    year = current_year - 1
else:
    year = current_year

start_date = datetime(year, selected_month_num, 1)
_, last_day = monthrange(year, selected_month_num)
end_date = datetime(year, selected_month_num, last_day)

start_unix = int(start_date.timestamp())
end_unix = int(end_date.timestamp() + 86399)


if st.button("Get Weather Data"):
    summary_data = []
    detailed_data = {} 

    for location, (lat, lon) in locations.items():
        current_start = start_unix
        all_data = []

        while current_start < end_unix:
            current_end = min(current_start + 604800 - 1, end_unix)
            url = f"https://history.openweathermap.org/data/2.5/history/city?lat={lat}&lon={lon}&type=hour&start={current_start}&end={current_end}&units=imperial&appid={api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                all_data.extend(data.get('list', []))
                current_start += 604800
            else:
                st.error(f"Failed to fetch weather data for {location}.")
                break

        if all_data:
            df = pd.DataFrame([{
                'date': datetime.fromtimestamp(item['dt'], tz=timezone.utc),
                'Temperature (F)': item['main']['temp'],
                'Min Temperature': item['main']['temp_min'],
                'Max Temperature': item['main']['temp_max'],
            } for item in all_data])


            df['date_only'] = df['date'].dt.date
            
            avg_high = df.groupby('date_only')['Max Temperature'].max().mean()
            avg_low = df.groupby('date_only')['Min Temperature'].min().mean()
            num_observations = len(df)
            num_hours_above_threshold = df[df['Temperature (F)'] > temp_threshold].shape[0]



            summary_data.append({
                'Location': location,
                'Avg High Temp (°F)': round(avg_high, 2),
                'Avg Low Temp (°F)': round(avg_low, 2),
                'Observations': num_observations,
                'Hours Above Threshold': num_hours_above_threshold,
                
            })


            detailed_data[location] = df


    summary_df = pd.DataFrame(summary_data)
    st.write("Summary of Weather Data:")
    st.write(summary_df)

    for location, df in detailed_data.items():


        daily_highs = df.set_index('date').resample('D')['Max Temperature'].max()
        fig_highs = px.line(daily_highs, title=f'Daily High Temperatures for {location}')
        fig_highs.update_xaxes(title_text='Date')
        fig_highs.update_yaxes(title_text='Max Temperature (°F)')
        st.plotly_chart(fig_highs)
        
        df['hour'] = df['date'].dt.hour
        fig_box = px.box(df, x='hour', y='Temperature (F)', title=f'Hourly Temperature Distribution for {location}')
        st.plotly_chart(fig_box)

        daily_stats = df.set_index('date').resample('D').agg({
            'Min Temperature': 'min',
            'Temperature (F)': 'mean',
            'Max Temperature': 'max'
        }).reset_index()
        daily_combined = pd.melt(daily_stats, id_vars=['date'], value_vars=['Min Temperature', 'Temperature (F)', 'Max Temperature'],
                                 var_name='Temperature Type', value_name='Temperature')
        fig_daily_box = px.box(daily_combined, x='Temperature Type', y='Temperature', title=f'Temperature Distribution for {location} Over the Month')
        st.plotly_chart(fig_daily_box)


st.markdown("---")
st.write("Powered by [Streamlit](https://streamlit.io/)")