# 🌦️ Weather

### 🛰️ NASA Space Apps Challenge 2025 – Challenge: *“Weather Odds — How Likely Is It?”*

> **Know your weather odds — months in advance.**  
> A personalized dashboard powered by NASA Earth observation data that helps users understand the **probability of extreme weather** (heat, cold, rain, wind, humidity) for any location and time of year.

---

## 🚀 Project Overview

Even though everyone hopes for perfect weather, it rarely happens — outdoor events, travel, and safety often depend on unpredictable conditions.  
Our project solves this by using **NASA’s historical weather data** to calculate the **likelihood of different weather extremes** for any location and date.  

This is not a forecast; it’s a **probability-based insight tool** built on NASA’s open Earth observation datasets.

---

## 🧩 Features

- 🌍 **Interactive Map:** Search any city or drop a pin on the map.  
- 📅 **Select Any Date:** Choose a past or future date to analyze.  
- ☁️ **Custom Weather Metrics:** Very hot, very cold, wet, windy, or uncomfortable.  
- 📊 **Dynamic Visuals:** Bar charts, line trends, and text insights.  
- 🧠 **Historical & Predictive Analysis:** Uses 10 years of NASA POWER data to compute weather probabilities and detect trends.  
- 💾 **Download Data:** Export query results as CSV or JSON.  

---

## 🛰️ NASA Data Used

**NASA POWER (Prediction Of Worldwide Energy Resources) API**  
Endpoint: [`https://power.larc.nasa.gov/api/temporal/daily/point`](https://power.larc.nasa.gov/api/temporal/daily/point)  

**Data Parameters:**
- `T2M` → Air Temperature at 2m  
- `PRECTOTCORR` → Corrected Precipitation  
- `WS2M` → Wind Speed at 2m  
- `RH2M` → Relative Humidity at 2m  

**How it’s used:**  
Historical data (10 years) is fetched for a given lat/lon and analyzed to compute probabilities for extreme heat, cold, rainfall, wind, and humidity discomfort.

---

## ⚙️ Tech Stack

**Frontend:**  
- HTML5, CSS3  
- JavaScript (Vanilla)  
- [Leaflet.js](https://leafletjs.com/) for interactive mapping  

**Backend:**  
- Python (Flask)  
- Pandas, Requests  
- NASA POWER API Integration  

**Deployment:**  
- Localhost or Render / GitHub Pages (for frontend)  
- Flask backend (PythonAnywhere, Render, etc.)

---

## 🔄 How It Works

1. **User selects** a city or pin on the map and a date.  
2. **Flask backend** retrieves NASA POWER data for the location.  
3. **Probabilities** of extreme weather are computed using historical data thresholds.  
4. **Predictions** are generated for future dates using recent trends.  
5. **Dashboard updates** dynamically with charts, summaries, and confidence levels.  

---

## 📸 Screenshots

| Dashboard | Trends | Map |
|------------|---------|-----|
| ![Dashboard Screenshot](docs/dashboard.png) | ![Line Chart](docs/trends.png) | ![Map View](docs/map.png) |
