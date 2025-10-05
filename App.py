from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
import json
import csv

app = Flask(__name__)
CORS(app)

# NASA's weather data API
NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

def find_city_coordinates(city_name):
    """Find latitude and longitude for a city name"""
    if not city_name:
        return 24.8607, 67.0011  # Default to Karachi
    
    try:
        # Use OpenStreetMap to find city coordinates
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_name, "format": "json", "limit": 1}
        headers = {"User-Agent": "WeatherApp/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
        else:
            return 24.8607, 67.0011  # Fallback to Karachi
    except Exception:
        return 24.8607, 67.0011  # Fallback if anything goes wrong

def find_location_name(lat, lon):
    """Convert coordinates back to a readable location name"""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat, "lon": lon, "format": "json",
            "zoom": 10, "addressdetails": 1
        }
        headers = {"User-Agent": "WeatherApp/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        address = result.get("address", {})
        
        # Try to get city, town, or region name
        city = address.get("city") or address.get("town") or address.get("village")
        region = address.get("state") or address.get("county")
        
        if city and region:
            return f"{city}, {region}"
        elif city:
            return city
        elif region:
            return region
        else:
            return f"{lat:.2f}, {lon:.2f}"  # Show coordinates if no name found
    except Exception:
        return f"{lat:.2f}, {lon:.2f}"

def get_weather_thresholds(lat, lon):
    """Define what counts as 'extreme' weather for different regions"""
    # Coastal areas (like Karachi) - lower heat threshold due to humidity
    if 24.0 <= lat <= 25.5 and 66.0 <= lon <= 68.0:
        return {"hot": 38, "cold": 10, "wet": 15, "windy": 8}
    # Northern mountains - much colder, less rain
    elif 34.0 <= lat <= 37.0 and 70.0 <= lon <= 77.0:
        return {"hot": 32, "cold": -5, "wet": 8, "windy": 12}
    # Plains (like Lahore, Islamabad) - standard thresholds
    elif 30.0 <= lat <= 34.0:
        return {"hot": 40, "cold": 0, "wet": 12, "windy": 10}
    # Default for other locations
    else:
        return {"hot": 35, "cold": 5, "wet": 10, "windy": 8}

def get_date_range(selected_date, years=10):
    """Calculate start and end dates for weather data"""
    try:
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        today = datetime.now()
        
        # Don't go beyond today for end date
        end_date = min(date_obj, today).strftime('%Y%m%d')
        # Start 10 years back
        start_date = (today - timedelta(days=365 * years)).strftime('%Y%m%d')
        
        return start_date, end_date
    except Exception:
        # Fallback to recent 10 years if date parsing fails
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365 * years)).strftime('%Y%m%d')
        return start_date, end_date

def get_nasa_weather_data(lat, lon, start, end):
    """Fetch historical weather data from NASA"""
    params = {
        "parameters": "T2M,PRECTOTCORR,WS2M,RH2M",  # Temperature, Rain, Wind, Humidity
        "community": "AG",
        "longitude": lon, "latitude": lat,
        "start": start, "end": end, "format": "JSON"
    }
    
    try:
        response = requests.get(NASA_API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"properties": {"parameter": {}}}  # Return empty data on error

def calculate_prediction_confidence(weather_data, target_date):
    """How confident are we in this prediction?"""
    if weather_data.empty:
        return 0  # No data = no confidence
    
    # More historical data = more confidence
    data_amount_confidence = min(100, len(weather_data) / 3650 * 100)
    
    # Recent data = more confidence
    if not weather_data.empty:
        latest_date = weather_data.index.max()
        days_since_latest = (datetime.now() - latest_date).days
        recency_confidence = max(0, 100 - (days_since_latest * 2))
    else:
        recency_confidence = 0
    
    # Future predictions are less certain
    future_uncertainty = 0
    if target_date > datetime.now():
        days_in_future = (target_date - datetime.now()).days
        future_uncertainty = min(30, days_in_future * 2)
    
    total_confidence = (data_amount_confidence * 0.4 + recency_confidence * 0.6) - future_uncertainty
    return max(10, min(95, total_confidence))  # Keep between 10-95%

def generate_future_timeseries(target_date_str, historical_df, lat, lon):
    """Generate future time series data based on historical patterns"""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    
    # Create future months for the time series
    future_months = []
    for i in range(6):  # Show next 6 months including target month
        month_date = target_date.replace(day=1) + timedelta(days=30*i)
        future_months.append(month_date)
    
    time_series = []
    
    if not historical_df.empty:
        for month_date in future_months:
            # Get historical data for this month
            month_data = historical_df[historical_df.index.month == month_date.month]
            
            if not month_data.empty:
                # Use historical averages for this month
                avg_temp = month_data["temp"].mean()
                avg_rain = month_data["rain"].mean()
                avg_wind = month_data["wind"].mean()
                
                # Apply seasonal adjustments
                seasonal_adj = get_seasonal_adjustments(month_date.month, lat)
                adjusted_temp = avg_temp * seasonal_adj["heat"]
                adjusted_rain = avg_rain * seasonal_adj["rain"]
                adjusted_wind = avg_wind * seasonal_adj["wind"]
                
                time_series.append({
                    "date": month_date.strftime("%Y-%m"),
                    "hot": round(float(adjusted_temp), 1),
                    "cold": round(float(adjusted_temp), 1),
                    "wet": round(float(adjusted_rain), 1),
                    "windy": round(float(adjusted_wind), 1)
                })
            else:
                # Fallback values if no historical data
                time_series.append({
                    "date": month_date.strftime("%Y-%m"),
                    "hot": 25.0, "cold": 25.0, "wet": 5.0, "windy": 5.0
                })
    else:
        # Default future time series if no historical data
        for month_date in future_months:
            time_series.append({
                "date": month_date.strftime("%Y-%m"),
                "hot": 25.0, "cold": 25.0, "wet": 5.0, "windy": 5.0
            })
    
    return time_series

def predict_future_weather(historical_data, target_date_str, lat, lon):
    """Predict future weather probabilities"""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    today = datetime.now()
    thresholds = get_weather_thresholds(lat, lon)

    # Default probabilities
    predictions = {
        "very_hot": 0.0, "very_cold": 0.0, 
        "very_wet": 0.0, "very_windy": 0.0, 
        "uncomfortable": 0.0
    }

    # Only predict if we have data and it's a future date
    if target_date > today and not historical_data.empty:
        target_month = target_date.month
        
        # Look at historical data for same month
        same_month_history = historical_data[historical_data.index.month == target_month]
        recent_trend = historical_data.last('90D')  # Last 3 months trend
        
        if not same_month_history.empty:
            # What happened in past years this month?
            historical_hot = (same_month_history["temp"] > thresholds["hot"]).mean() * 100
            historical_cold = (same_month_history["temp"] < thresholds["cold"]).mean() * 100
            historical_wet = (same_month_history["rain"] > thresholds["wet"]).mean() * 100
            historical_windy = (same_month_history["wind"] > thresholds["windy"]).mean() * 100
            
            # Factor in recent weather trends
            if not recent_trend.empty:
                recent_hot = (recent_trend["temp"] > thresholds["hot"]).mean() * 100
                recent_wet = (recent_trend["rain"] > thresholds["wet"]).mean() * 100
                recent_windy = (recent_trend["wind"] > thresholds["windy"]).mean() * 100
                
                # Blend historical patterns with recent trends
                hot_prob = (historical_hot * 0.6) + (recent_hot * 0.4)
                wet_prob = (historical_wet * 0.6) + (recent_wet * 0.4)
                windy_prob = (historical_windy * 0.6) + (recent_windy * 0.4)
            else:
                hot_prob = historical_hot
                wet_prob = historical_wet
                windy_prob = historical_windy
            
            cold_prob = historical_cold  # Cold weather less affected by recent trends
            
            # Adjust for seasonal patterns
            season_adjustment = get_seasonal_adjustments(target_month, lat)
            hot_prob *= season_adjustment["heat"]
            wet_prob *= season_adjustment["rain"]
            windy_prob *= season_adjustment["wind"]
            
            # Calculate discomfort (hot + humid)
            if "humidity" in historical_data.columns:
                uncomfortable_days = same_month_history[
                    (same_month_history["temp"] > 30) & 
                    (same_month_history["humidity"] > 70)
                ]
                discomfort_prob = len(uncomfortable_days) / len(same_month_history) * 100
            else:
                # Estimate discomfort from other factors
                discomfort_prob = (hot_prob * 0.5 + wet_prob * 0.3 + windy_prob * 0.2)
            
            predictions = {
                "very_hot": round(min(100, max(0, hot_prob)), 1),
                "very_cold": round(min(100, max(0, cold_prob)), 1),
                "very_wet": round(min(100, max(0, wet_prob)), 1),
                "very_windy": round(min(100, max(0, windy_prob)), 1),
                "uncomfortable": round(min(100, max(0, discomfort_prob)), 1)
            }

    return predictions

def get_seasonal_adjustments(month, lat):
    """Adjust probabilities based on season and location"""
    adjustments = {"heat": 1.0, "rain": 1.0, "wind": 1.0}
    
    # Northern hemisphere seasons
    if lat >= 0:
        if month in [6, 7, 8]:  # Summer
            adjustments["heat"] = 1.3  # 30% hotter in summer
            adjustments["rain"] = 1.1
        elif month in [12, 1, 2]:  # Winter
            adjustments["heat"] = 0.7  # 30% cooler in winter
            adjustments["wind"] = 1.2  # 20% windier
        elif month in [7, 8, 9]:  # Monsoon season
            adjustments["rain"] = 1.5  # 50% more rainy
            adjustments["heat"] = 0.9  # Slightly cooler
    
    return adjustments

def analyze_historical_weather(nasa_data, target_date_str, lat, lon):
    """Analyze past weather data for probabilities"""
    if "properties" not in nasa_data or "parameter" not in nasa_data["properties"]:
        return {"very_hot": 0, "very_cold": 0, "very_wet": 0, "very_windy": 0, "uncomfortable": 0}, []

    daily_data = nasa_data["properties"]["parameter"]
    if not daily_data.get("T2M"):
        return {"very_hot": 0, "very_cold": 0, "very_wet": 0, "very_windy": 0, "uncomfortable": 0}, []

    # Organize the weather data
    weather_records = {
        "date": list(daily_data["T2M"].keys()),
        "temp": list(daily_data["T2M"].values()),
        "rain": list(daily_data["PRECTOTCORR"].values()),
        "wind": list(daily_data["WS2M"].values())
    }
    
    # Include humidity if available
    if "RH2M" in daily_data:
        weather_records["humidity"] = list(daily_data["RH2M"].values())
    
    df = pd.DataFrame(weather_records)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date")

    # Use appropriate thresholds for this region
    thresholds = get_weather_thresholds(lat, lon)
    
    # Calculate how often extreme weather occurred
    hot_days_percent = (df["temp"] > thresholds["hot"]).mean() * 100
    cold_days_percent = (df["temp"] < thresholds["cold"]).mean() * 100
    wet_days_percent = (df["rain"] > thresholds["wet"]).mean() * 100
    windy_days_percent = (df["wind"] > thresholds["windy"]).mean() * 100

    # Calculate uncomfortable days (hot + humid)
    if "humidity" in df.columns:
        uncomfortable_days = df[(df["temp"] > 30) & (df["humidity"] > 70)]
        uncomfortable_percent = len(uncomfortable_days) / len(df) * 100
    else:
        uncomfortable_percent = hot_days_percent * 0.8  # Estimate

    probabilities = {
        "very_hot": round(min(100, max(0, hot_days_percent)), 1),
        "very_cold": round(min(100, max(0, cold_days_percent)), 1),
        "very_wet": round(min(100, max(0, wet_days_percent)), 1),
        "very_windy": round(min(100, max(0, windy_days_percent)), 1),
        "uncomfortable": round(min(100, max(0, uncomfortable_percent)), 1)
    }

    # Create smoothed monthly trends for the chart
    monthly_data = df.resample("M").mean(numeric_only=True)
    
    # Smooth the data with 3-month averages
    if len(monthly_data) >= 3:
        monthly_data["temp_smooth"] = monthly_data["temp"].rolling(window=3, min_periods=1).mean()
        monthly_data["rain_smooth"] = monthly_data["rain"].rolling(window=3, min_periods=1).mean()
        monthly_data["wind_smooth"] = monthly_data["wind"].rolling(window=3, min_periods=1).mean()
    else:
        monthly_data["temp_smooth"] = monthly_data["temp"]
        monthly_data["rain_smooth"] = monthly_data["rain"]
        monthly_data["wind_smooth"] = monthly_data["wind"]
    
    # Get last 12 months for the trend chart
    recent_months = monthly_data.tail(12).reset_index()
    
    time_trends = []
    for _, month_data in recent_months.iterrows():
        time_trends.append({
            "date": month_data["date"].strftime("%Y-%m"),
            "hot": round(float(month_data["temp_smooth"]), 1),
            "cold": round(float(month_data["temp_smooth"]), 1),  # Same as hot for now
            "wet": round(float(month_data["rain_smooth"]), 1),
            "windy": round(float(month_data["wind_smooth"]), 1)
        })

    return probabilities, time_trends

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check_weather():
    data = request.get_json() or {}
    city = data.get("city", "Karachi").lower().strip()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    coordinates = data.get("lat_lon")

    # Get location coordinates
    if coordinates:
        try:
            lat, lon = map(float, coordinates.split(","))
            location_name = find_location_name(lat, lon)
        except Exception:
            lat, lon = find_city_coordinates(city)
            location_name = city.title()
    else:
        lat, lon = find_city_coordinates(city)
        location_name = city.title()

    # Get weather data date range
    start_date, end_date = get_date_range(date)
    nasa_data = get_nasa_weather_data(lat, lon, start_date, end_date)
    
    target_date = datetime.strptime(date, '%Y-%m-%d')
    
    if target_date > datetime.now():
        # Future date - use prediction
        daily_data = nasa_data.get("properties", {}).get("parameter", {})
        historical_df = pd.DataFrame()
        
        if daily_data.get("T2M"):
            historical_records = {
                "date": list(daily_data["T2M"].keys()),
                "temp": list(daily_data["T2M"].values()),
                "rain": list(daily_data["PRECTOTCORR"].values()),
                "wind": list(daily_data["WS2M"].values())
            }
            if "RH2M" in daily_data:
                historical_records["humidity"] = list(daily_data["RH2M"].values())
            
            historical_df = pd.DataFrame(historical_records)
            historical_df["date"] = pd.to_datetime(historical_df["date"], format="%Y%m%d")
            historical_df = historical_df.set_index("date")
        
        probabilities = predict_future_weather(historical_df, date, lat, lon)
        time_series = generate_future_timeseries(date, historical_df, lat, lon)
        confidence = calculate_prediction_confidence(historical_df, target_date)
    else:
        # Past date - use historical analysis
        probabilities, time_series = analyze_historical_weather(nasa_data, date, lat, lon)
        confidence = 95  # High confidence for past data

    return jsonify({
        "city": location_name,
        "date": date,
        "probabilities": probabilities,
        "time_series": time_series,
        "coords": [lat, lon],
        "confidence": round(confidence, 1)
    })

@app.route("/download/csv", methods=["POST"])
def download_csv():
    data = request.get_json() or {}
    city = data.get("city", "Karachi").lower().strip()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    # This would need to be implemented based on your data structure
    # For now, returning a simple CSV structure
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Weather Data for", city, "on", date])
    writer.writerow([])
    writer.writerow(["Feature", "Value"])
    writer.writerow(["Location", city])
    writer.writerow(["Date", date])
    writer.writerow(["Note", "Full data download coming soon!"])

    csv_data = output.getvalue()
    response = make_response(csv_data)
    filename = f"{city}_weather_{date}.csv".replace(" ", "_")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/download/json", methods=["POST"])
def download_json():
    data = request.get_json() or {}
    city = data.get("city", "Karachi").lower().strip()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Simple JSON structure for download
    weather_data = {
        "location": city,
        "date": date,
        "data_available": True,
        "note": "Complete weather data export feature in development"
    }

    response = make_response(json.dumps(weather_data, indent=2))
    filename = f"{city}_weather_{date}.json".replace(" ", "_")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "application/json"
    return response

if __name__ == "__main__":
    app.run(debug=True)
