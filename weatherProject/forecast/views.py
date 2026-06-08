from django.shortcuts import render
import os 
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

API_KEY = 'ce475fd4598d135fc1601b2abc2c1472'
BASE_URL = 'https://api.openweathermap.org/data/2.5/'

def get_current_weather(city):
    url = f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        raise Exception(f"Error fetching weather data: {data.get('message', 'Unknown error')}")

    return {
        'city': data['name'],
        'current_temp': round(data['main']['temp'], 1),
        'feels_like': round(data['main']['feels_like'], 1),
        'temp_min': round(data['main']['temp_min'], 1),
        'temp_max': round(data['main']['temp_max'], 1),
        'humidity': round(data['main']['humidity'], 1),
        'description': data['weather'][0]['description'],
        'country': data['sys']['country'],
        'wind_gust_dir': data['wind'].get('deg', 0),
        'pressure': data['main']['pressure'],
        'Wind_Gust_Speed': data['wind'].get('speed', 0),
        'clouds':data['clouds']['all'],
        'Visibility':data['visibility'],
    }

def read_historical_data(filename):
    df = pd.read_csv(filename)
    df = df.dropna().drop_duplicates()
    return df

# PREPARE DATA FOR RAIN PREDICTION
# ---------------------------------
def prepare_data(data):
    le = LabelEncoder()
    data = data.copy()
    data['WindGustDir'] = le.fit_transform(data['WindGustDir'])
    data['RainTomorrow'] = le.fit_transform(data['RainTomorrow'])
    
    X = data[['MinTemp', 'MaxTemp', 'WindGustDir', 'WindGustSpeed', 'Humidity', 'Pressure', 'Temp']]
    y = data['RainTomorrow']
    
    return X, y, le

def train_rain_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=150, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print(f"Mean squared error for rain model: {mse:.4f}")
    return model

def prepare_regression_data(data, feature, window_size=3):
    """
    Builds a sliding window dataset for time series regression.
    Example: predicts next Temp from last 3 values.
    """
    values = data[feature].values
    X, y = [], []
    for i in range(len(values) - window_size):
        X.append(values[i:i+window_size])
        y.append(values[i + window_size])
    return np.array(X), np.array(y)

def train_regression_model(X, y):
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X, y)
    return model

# PREDICT FUTURE TEMPERATURE/HUMIDITY
# ---------------------------------
def predict_future(model, recent_values, steps=5):
    """
    Predicts next `steps` future values given recent window.
    """
    predictions = []
    current_window = list(recent_values)
    
    for _ in range(steps):
        next_value = model.predict([current_window])[-1]
        predictions.append(next_value)
        current_window = current_window[1:] + [next_value]
    return predictions

def weather_view(request):
    context = {}  # always define context first

    if request.method == 'POST':
        city = request.POST.get('city')

        if city:  # ensure user entered a city
            try:
                # Get current weather
                current_weather = get_current_weather(city)

                csv_path = os.path.join(
                    'C:\\Users\\91983\\OneDrive\\Desktop\\weather_prediction\\weather.csv'
                )

                historical_data = read_historical_data(csv_path)

                # Train rain model
                X, y, le = prepare_data(historical_data)
                rain_model = train_rain_model(X, y)

                # Convert wind degree to compass direction
                wind_deg = current_weather['wind_gust_dir'] % 360
                compass_points = [
                    ("N", 348.75, 360), ("N", 0, 11.25), ("NNE", 11.25, 33.75),
                    ("NE", 33.75, 56.25), ("ENE", 56.25, 78.75), ("E", 78.75, 101.25),
                    ("ESE", 101.25, 123.75), ("SE", 123.75, 146.25), ("SSE", 146.25, 168.75),
                    ("S", 168.75, 191.25), ("SSW", 191.25, 213.75), ("SW", 213.75, 236.25),
                    ("WSW", 236.25, 258.75), ("W", 258.75, 281.25), ("WNW", 281.25, 303.75),
                    ("NW", 303.75, 326.25), ("NNW", 326.25, 348.75)
                ]
                compass_direction = next(
                    (point for point, start, end in compass_points if start <= wind_deg < end),
                    "N"
                )

                # Encode wind direction safely
                if compass_direction in le.classes_:
                    compass_direction_encoded = le.transform([compass_direction])[0]
                else:
                    compass_direction_encoded = le.transform([le.classes_[0]])[0]

                # Prepare input for rain prediction
                current_data = {
                    'MinTemp': current_weather['temp_min'],
                    'MaxTemp': current_weather['temp_max'],
                    'WindGustDir': compass_direction_encoded,
                    'WindGustSpeed': current_weather['Wind_Gust_Speed'],
                    'Humidity': current_weather['humidity'],
                    'Pressure': current_weather['pressure'],
                    'Temp': current_weather['current_temp']
                }

                current_df = pd.DataFrame([current_data])
                rain_prediction = rain_model.predict(current_df)[0]

                # Train regression models (temperature & humidity)
                X_temp, y_temp = prepare_regression_data(historical_data, 'Temp')
                X_hum, y_hum = prepare_regression_data(historical_data, 'Humidity')

                temp_model = train_regression_model(X_temp, y_temp)
                hum_model = train_regression_model(X_hum, y_hum)

                # Prepare recent 3 values for future predictions
                recent_temp = historical_data['Temp'].values[-3:]
                recent_hum = historical_data['Humidity'].values[-3:]

                future_temp = predict_future(temp_model, recent_temp)
                future_humidity = predict_future(hum_model, recent_hum)

                # Time formatting
                timezone = pytz.timezone('Asia/Kolkata')
                now = datetime.now(timezone)
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                future_times = [(next_hour + timedelta(hours=i)).strftime("%H:00") for i in range(5)]

                # unpack for template
                time1, time2, time3, time4, time5 = future_times
                temp1, temp2, temp3, temp4, temp5 = future_temp
                hum1, hum2, hum3, hum4, hum5 = future_humidity

                # build context
                context = {
                    'location': city,
                    'current_temp': current_weather['current_temp'],
                    'MinTemp': current_weather['temp_min'],
                    'MaxTemp': current_weather['temp_max'],
                    'feels_like': current_weather['feels_like'],
                    'humidity': current_weather['humidity'],
                    'clouds': current_weather['clouds'],
                    'description': current_weather['description'],
                    'city': current_weather['city'],
                    'country': current_weather['country'],
                    'time': now.strftime("%I:%M %p"),
                    'date': now.strftime("%B %d, %Y"),
                    'wind': current_weather['Wind_Gust_Speed'],
                    'pressure': current_weather['pressure'],
                    'visibility': current_weather['Visibility'],

                    'time1': time1, 'time2': time2, 'time3': time3, 'time4': time4, 'time5': time5,
                    'temp1': f"{round(temp1, 1)}", 'temp2': f"{round(temp2, 1)}", 'temp3': f"{round(temp3, 1)}",
                    'temp4': f"{round(temp4, 1)}", 'temp5': f"{round(temp5, 1)}",
                    'hum1': f"{round(hum1, 1)}", 'hum2': f"{round(hum2, 1)}", 'hum3': f"{round(hum3, 1)}",
                    'hum4': f"{round(hum4, 1)}", 'hum5': f"{round(hum5, 1)}",
                    'rain_prediction': "Yes" if rain_prediction == 1 else "No",
                }

            except Exception as e:
                context = {'error': str(e)}

        else:
            context = {'error': "Please enter a valid city name."}

    # Always return a response
    return render(request, 'weather.html', context)

