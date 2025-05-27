"""Requires gradio==4.27.0"""
import io
import os
import json
import time
import datetime
import numpy as np

from uuid import uuid4
from PIL import Image
from math import radians, sin, cos, sqrt, asin, exp
from os.path import join
from collections import defaultdict
from itertools import tee

import matplotlib.style as mplstyle
mplstyle.use(['fast'])
import pandas as pd

import gradio as gr
import reverse_geocoder as rg
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

from gradio_folium import Folium
from geographiclib.geodesic import Geodesic
from folium import Map, Element, LatLngPopup, Marker, PolyLine, FeatureGroup
from folium.map import LayerControl
from folium.plugins import BeautifyIcon

MPL = False
IMAGE_FOLDER = './images'
CSV_FILE = './select.csv'
BASE_LOCATION = [0, 23]
RULES = """
<div class="hero-section">
    <div class="hero-content">
        <h1 class="hero-title"><span class="title-icon"></span>PRIV-LOC</h1>
        <h2 class="hero-subtitle">Geolocation Privacy Challenge</h2>
        <div class="hero-description">
            <p>Challenge yourself against state-of-the-art AI models in a real-time geolocation game. Can you identify photo locations better than Claude, GPT, Gemini, and Qwen?</p>
        </div>
    </div>
    <div class="globe-container">
        <img class="rotating-globe" alt="Rotating globe" src="https://upload.wikimedia.org/wikipedia/commons/6/6b/Rotating_globe.gif">
    </div>
</div>

<div class="info-grid">
    <div class="info-card">
        <h3>🎯 How to Play</h3>
        <p>Click on the map where you think the image was taken, then click <strong>Select</strong> to confirm your guess.</p>
    </div>
    
    <div class="info-card">
        <h3>🤖 Your Competition</h3>
        <ul class="ai-models">
            <li><span class="model-badge claude">Claude</span> Anthropic</li>
            <li><span class="model-badge gpt">GPT</span> OpenAI</li>
            <li><span class="model-badge gemini">Gemini</span> Google</li>
            <li><span class="model-badge qwen">Qwen</span> Alibaba</li>
        </ul>
    </div>
    
    <div class="info-card">
        <h3>📊 Scoring System</h3>
        <p>Earn up to <strong>5000 points</strong> per image based on accuracy. The closer your guess, the higher your score!</p>
        <div class="formula-container">
            <img class="formula" src="https://latex.codecogs.com/svg.image?g(d)=5000\exp\left(\\frac{-d}{1492.7}\\right)" alt="Scoring formula" />
        </div>
    </div>
</div>

<div class="challenge-section">
    <h2>🏆 Ready for the Challenge?</h2>
    <p>This isn't just a game—it's cutting-edge research in AI privacy and geolocation. Your performance helps us understand how humans compare to AI in visual location detection.</p>
</div>
"""

css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary-color: #2563eb;
    --secondary-color: #1e40af;
    --accent-color: #f59e0b;
    --success-color: #10b981;
    --danger-color: #ef4444;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-accent: #f1f5f9;
    --border-color: #e2e8f0;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --gradient-accent: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.gradio-container {
    max-width: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* Start Button Specific Styling */
.gradio-container [id="start-button"] {
    width: 200px !important;
    margin: 0 auto !important;
    display: block !important;
}

/* Hero Section */
.hero-section {
    background: var(--gradient-primary);
    padding: 4rem 2rem;
    text-align: center;
    color: white;
    position: relative;
    overflow: hidden;
    margin-bottom: 2rem;
}

.logo-container {
    margin-bottom: 1.5rem;
}

.logo {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    box-shadow: var(--shadow-xl);
    background: white;
    padding: 10px;
    margin-bottom: 1rem;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="50" cy="50" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
    opacity: 0.1;
}

.hero-content {
    position: relative;
    z-index: 2;
    max-width: 800px;
    margin: 0 auto;
}

.hero-title {
    font-size: 4rem;
    font-weight: 800;
    margin: 0 0 1rem 0;
    background: linear-gradient(45deg, #fff, #e0e7ff);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.hero-subtitle {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0 0 2rem 0;
    opacity: 0.9;
}

.hero-description p {
    font-size: 1.2rem;
    line-height: 1.6;
    opacity: 0.8;
    margin: 0;
}

.globe-container {
    margin-top: 2rem;
}

.rotating-globe {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    box-shadow: var(--shadow-xl);
    filter: brightness(1.1);
}

/* Info Grid */
.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 2rem;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

.info-card {
    background: var(--bg-primary);
    border-radius: 16px;
    padding: 2rem;
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--border-color);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.info-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-xl);
}

.info-card h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.info-card p {
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0 0 1rem 0;
}

.ai-models {
    list-style: none;
    padding: 0;
    margin: 0;
}

.ai-models li {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0;
    color: var(--text-secondary);
}

.model-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 600;
    color: white;
    min-width: 60px;
    text-align: center;
}

.model-badge.claude { background: #8b5cf6; }
.model-badge.gpt { background: #10b981; }
.model-badge.gemini { background: #3b82f6; }
.model-badge.qwen { background: #f59e0b; }

.formula-container {
    text-align: center;
    margin: 1rem 0;
}

.formula {
    max-width: 100%;
    height: auto;
    background: var(--bg-accent);
    padding: 1rem;
    border-radius: 8px;
}

/* Challenge Section */
.challenge-section {
    background: var(--bg-primary);
    padding: 3rem 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 800px;
    border-radius: 16px;
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--border-color);
}

.challenge-section h2 {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 1rem 0;
}

.challenge-section p {
    font-size: 1.1rem;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0;
}

/* Game Interface */
.game-container {
    background: var(--bg-primary);
    border-radius: 16px;
    padding: 2rem;
    margin: 2rem;
    box-shadow: var(--shadow-xl);
    border: 1px solid var(--border-color);
}

/* Buttons */
button {
    background: var(--gradient-primary) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    color: white !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: var(--shadow-md) !important;
}

button:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-lg) !important;
    filter: brightness(1.05) !important;
}

button:active {
    transform: translateY(0) !important;
}

.secondary-btn {
    background: var(--gradient-secondary) !important;
}

.success-btn {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
}

.danger-btn {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
}

/* Results and Stats */
.result-card {
    background: var(--bg-primary);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
}

.score-display {
    font-size: 1.25rem;
    font-weight: 600;
    text-align: center;
    padding: 1rem;
    background: var(--gradient-accent);
    color: white;
    border-radius: 12px;
    margin: 1rem 0;
}

/* Dataframe Styling */
.dataframe {
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-md) !important;
}

.dataframe table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
}

.dataframe th {
    background: var(--gradient-primary) !important;
    color: white !important;
    padding: 1rem !important;
    font-weight: 600 !important;
}

.dataframe td {
    padding: 0.75rem 1rem !important;
    border-bottom: 1px solid var(--border-color) !important;
}

.dataframe tr:hover {
    background: var(--bg-accent) !important;
}

/* Image containers */
.image-container {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--border-color);
}

/* Progress indicator */
.progress-indicator {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    text-align: center;
    padding: 1rem;
    background: var(--bg-accent);
    border-radius: 12px;
    margin: 1rem 0;
}

/* Responsive Design */
@media (max-width: 768px) {
    .hero-title {
        font-size: 2.5rem;
    }
    
    .hero-subtitle {
        font-size: 1.25rem;
    }
    
    .info-grid {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
    
    .hero-section {
        padding: 2rem 1rem;
    }
    
    .game-container {
        margin: 1rem;
        padding: 1rem;
    }
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}

.fade-in {
    animation: fadeIn 0.6s ease-out;
}

.slide-in {
    animation: slideIn 0.6s ease-out;
}

/* Map and image styling */
.map-container, .image-container {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
    border: 2px solid var(--border-color);
    transition: transform 0.3s ease;
}

.map-container:hover, .image-container:hover {
    transform: scale(1.02);
}

/* End game styling */
.end-game-title {
    font-size: 3rem !important;
    font-weight: 800 !important;
    background: var(--gradient-primary) !important;
    background-clip: text !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    text-align: center !important;
    margin: 2rem 0 !important;
}

.end-game-subtitle {
    font-size: 1.5rem !important;
    color: var(--text-secondary) !important;
    text-align: center !important;
    margin: 1rem 0 2rem 0 !important;
}
"""

space_js = """
<script src="https://cdn.jsdelivr.net/npm/@rapideditor/country-coder@5.2/dist/country-coder.iife.min.js"></script>
<script>
function shortcuts(e) {
    var event = document.all ? window.event : e;
    switch (e.target.tagName.toLowerCase()) {
        case "input":
        case "textarea":
        break;
        default:
        if (e.key.toLowerCase() == " " && !e.shiftKey) {
            document.getElementById("latlon_btn").click();
        }
    }
}
function shortcuts_exit(e) {
    var event = document.all ? window.event : e;
    switch (e.target.tagName.toLowerCase()) {
        case "input":
        case "textarea":
        break;
        default:
        if (e.key.toLowerCase() == "e" && e.shiftKey) {
            document.getElementById("exit_btn").click();
        }
    }
}
document.addEventListener('keypress', shortcuts, false);
document.addEventListener('keypress', shortcuts_exit, false);

// Add fade-in animations to elements
document.addEventListener('DOMContentLoaded', function() {
    const elements = document.querySelectorAll('.info-card, .challenge-section');
    elements.forEach((el, index) => {
        setTimeout(() => {
            el.classList.add('fade-in');
        }, index * 200);
    });
});
</script>
"""

def sample_points_along_geodesic(start_lat, start_lon, end_lat, end_lon, min_length_km=2000, segment_length_km=5000, num_samples=None):
    geod = Geodesic.WGS84
    distance = geod.Inverse(start_lat, start_lon, end_lat, end_lon)['s12']
    if distance < min_length_km:
        return [(start_lat, start_lon), (end_lat, end_lon)]

    if num_samples is None:
        num_samples = min(int(distance / segment_length_km) + 1, 1000)
    point_distance = np.linspace(0, distance, num_samples)
    points = []
    for pd in point_distance:
        line = geod.InverseLine(start_lat, start_lon, end_lat, end_lon)
        g_point = line.Position(pd, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
        points.append((g_point['lat2'], g_point['lon2']))
    return points

class GeodesicPolyLine(PolyLine):
    def __init__(self, locations, min_length_km=2000, segment_length_km=1000, num_samples=None, **kwargs):
        kwargs1 = dict(min_length_km=min_length_km, segment_length_km=segment_length_km, num_samples=num_samples)
        assert len(locations) == 2, "A polyline must have at least two locations"
        start, end = locations
        geodesic_locs = sample_points_along_geodesic(start[0], start[1], end[0], end[1], **kwargs1)
        super().__init__(geodesic_locs, **kwargs)

def inject_javascript(folium_map):
    js = """
    document.addEventListener('DOMContentLoaded', function() {
        map_name_1.on('click', function(e) {
            window.state_data = e.latlng
        });
    });
    """
    folium_map.get_root().html.add_child(Element(f'<script>{js}</script>'))

def empty_map():
    return Map(location=BASE_LOCATION, zoom_start=1)

def make_map_(name="map_name", id="1"):
    map = Map(location=BASE_LOCATION, zoom_start=1)
    map._name, map._id = name, id

    LatLngPopup().add_to(map)
    inject_javascript(map)
    return map

def make_map(name="map_name", id="1", height=500):
    map = make_map_(name, id)
    fol = Folium(value=map, height=height, visible=False, elem_id='map-fol')
    return fol

def map_js():
    return  """
    (a, textBox) => {
        const iframeMap = document.getElementById('map-fol').getElementsByTagName('iframe')[0];
        const latlng = iframeMap.contentWindow.state_data;
        if (!latlng) { return [-1, -1]; }
        textBox = `${latlng.lat},${latlng.lng}`;
        document.getElementById('coords-tbox').getElementsByTagName('textarea')[0].value = textBox;
        var a = countryCoder.iso1A2Code([latlng.lng, latlng.lat]);
        if (!a) { a = 'nan'; }
        return [a, `${latlng.lat},${latlng.lng},${a}`];
    }
    """

def haversine(lat1, lon1, lat2, lon2):
    if (lat1 is None) or (lon1 is None) or (lat2 is None) or (lon2 is None):
        return 0
    R = 6371  # radius of the earth in km
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = (
        sin(dLat / 2.0) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2.0) ** 2
    )
    c = 2 * asin(sqrt(a))
    distance = R * c
    return distance

def geoscore(d):
    return 5000 * exp(-d / 1492.7)

def get_valid_coords(df, model):
    coords = []
    indices = []  # Keep track of original indices if needed
    for i in range(len(df)):
        try:
            lat = float(df[f'pred_lat_{model}'].iloc[i])
            lon = float(df[f'pred_lon_{model}'].iloc[i])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                coords.append((lat, lon))
                indices.append(i)
        except (ValueError, TypeError):
            # Skip if conversion fails or value is missing
            continue
    return coords, indices


def get_geocoder_results(df, model):
    coords = []
    index_map = []

    for i in range(len(df)):
        try:
            lat = float(df[f'pred_lat_{model}'].iloc[i])
            lon = float(df[f'pred_lon_{model}'].iloc[i])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                coords.append((lat, lon))
                index_map.append(i)
        except (ValueError, TypeError):
            continue

    # Safe query (disable multiprocessing for debugging)
    results = rg.search(coords, mode=1)

    # Initialize full-length result list
    full_results = [None] * len(df)

    # Populate valid entries
    for idx, res in zip(index_map, results):
        full_results[idx] = res

    # Fill invalid entries with default placeholder
    for i in range(len(df)):
        if full_results[i] is None:
            full_results[i] = {'name': 'Unknown', 'admin1': '', 'admin2': '', 'cc': ''}

    return full_results

def compute_scores(csv_file):
    df = pd.read_csv(csv_file)
    # Extract model names from columns that match pattern 'pred_lon_*'
    models = [col.replace('pred_lon_', '') for col in df.columns if col.startswith('pred_lon_')]

    if 'accuracy_country' not in df.columns:
        print('Computing scores... (this may take a while)')
        geocoders = rg.search([(row.true_lat, row.true_lon) for row in df.itertuples(name='Pandas')])
        df['city'] = [geocoder['name'] for geocoder in geocoders]
        df['area'] = [geocoder['admin2'] for geocoder in geocoders]
        df['region'] = [geocoder['admin1'] for geocoder in geocoders]
        df['country'] = [geocoder['cc'] for geocoder in geocoders]

        df['city_val'] = df['city'].apply(lambda x: 0 if pd.isna(x) or x == 'nan' else 1)
        df['area_val'] = df['area'].apply(lambda x: 0 if pd.isna(x) or x == 'nan' else 1)
        df['region_val'] = df['region'].apply(lambda x: 0 if pd.isna(x) or x == 'nan' else 1)
        df['country_val'] = df['country'].apply(lambda x: 0 if pd.isna(x) or x == 'nan' else 1)

        for model in models:
            df[f'distance_{model}'] = df.apply(lambda row: haversine(row['true_lat'], row['true_lon'], row[f'pred_lat_{model}'], row[f'pred_lon_{model}']), axis=1)
            df[f'score_{model}'] = df.apply(lambda row: geoscore(row[f'distance_{model}']), axis=1)

        
        for model in models:
            print(f"Computing geocoding accuracy ({model})...")
            geocoders = get_geocoder_results(df, model)

            df[f'pred_city_{model}'] = [geocoder['name'] for geocoder in geocoders]
            df[f'pred_area_{model}'] = [geocoder['admin2'] for geocoder in geocoders]
            df[f'pred_region_{model}'] = [geocoder['admin1'] for geocoder in geocoders]
            df[f'pred_country_{model}'] = [geocoder['cc'] for geocoder in geocoders]
        
            df[f'city_hit_{model}'] = [df['city'].iloc[i] != 'nan' and df[f'pred_city_{model}'].iloc[i] == df['city'].iloc[i] for i in range(len(df))]
            df[f'area_hit_{model}'] = [df['area'].iloc[i] != 'nan' and df[f'pred_area_{model}'].iloc[i] == df['area'].iloc[i] for i in range(len(df))]
            df[f'region_hit_{model}'] = [df['region'].iloc[i] != 'nan' and df[f'pred_region_{model}'].iloc[i] == df['region'].iloc[i] for i in range(len(df))]
            df[f'country_hit_{model}'] = [df['country'].iloc[i] != 'nan' and df[f'pred_country_{model}'].iloc[i] == df['country'].iloc[i] for i in range(len(df))]

            df[f'accuracy_city_{model}'] = [(0 if df['city_val'].iloc[:i].sum() == 0 else df[f'city_hit_{model}'].iloc[:i].sum()/df['city_val'].iloc[:i].sum())*100 for i in range(len(df))]
            df[f'accuracy_area_{model}'] = [(0 if df['area_val'].iloc[:i].sum() == 0 else df[f'area_hit_{model}'].iloc[:i].sum()/df['area_val'].iloc[:i].sum())*100 for i in range(len(df))]
            df[f'accuracy_region_{model}'] = [(0 if df['region_val'].iloc[:i].sum() == 0 else df[f'region_hit_{model}'].iloc[:i].sum()/df['region_val'].iloc[:i].sum())*100 for i in range(len(df))]
            df[f'accuracy_country_{model}'] = [(0 if df['country_val'].iloc[:i].sum() == 0 else df[f'country_hit_{model}'].iloc[:i].sum()/df['country_val'].iloc[:i].sum())*100 for i in range(len(df))]
        
        df.to_csv(csv_file, index=False)



if __name__ == "__main__":
    JSON_DATASET_DIR = 'results'



class Engine(object):
    def __init__(self, image_folder, csv_file, mpl=True, max_images=5):
        self.image_folder = image_folder
        self.csv_file = csv_file
        self.max_images = max_images
        self.load_images_and_coordinates(csv_file)
          
        # Initialize the score and distance lists
        self.index = 0
        self.stats = defaultdict(list)

        # Create the figure and canvas only once
        self.fig = plt.Figure(figsize=(10, 6))
        self.mpl = mpl
        if mpl:
            self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        self.tag = str(uuid4()) + datetime.datetime.now().strftime("__%Y_%m_%d_%H_%M_%S")

    def load_images_and_coordinates(self, csv_file):
        # Load the CSV
        df = pd.read_csv(csv_file)

        df['id'] = df['id'].astype(str)
        df = pd.concat([df[df['id'] == '495204901603170'], df[df['id'] != '495204901603170']])
        df = pd.concat([df[df['id'] == '732681614433401'], df[df['id'] != '732681614433401']])

        # order
        self.order = np.arange(len(df))
        np.random.shuffle(self.order)  # Shuffle the order array

        # If max_images is set, limit the number of images
        if self.max_images is not None:
            self.order = self.order[:self.max_images]

        # Reorder the DataFrame based on the shuffled order
        df = df.iloc[self.order].reset_index(drop=True)

        # Get the image filenames and their coordinates
        self.images = [os.path.join(self.image_folder, f"{img_path}.jpg") for img_path in df['id'].tolist()[:]]
        self.coordinates = df[['true_lon', 'true_lat']].values.tolist()[:]

        # compute the admins
        self.df = df
        self.admins = self.df[['city', 'area', 'region', 'country']].values.tolist()[:]

        model_names = [col.replace('pred_lon_', '') for col in df.columns if col.startswith('pred_lon_')]
        self.preds = {}
        self.models = []
        for model in model_names:
            lon_col, lat_col = f'pred_lon_{model}', f'pred_lat_{model}'
            self.preds[model] = self.df[[lon_col, lat_col]].values.tolist()[:]
            self.models.append(model)


    def isfinal(self):
        return self.index == len(self.images)-1

    def load_image(self):
        if self.index > len(self.images)-1:          
            self.master.update_idletasks()
            self.finish()

        self.set_clock()
        return self.images[self.index], '### ' + str(self.index + 1) + '/' + str(len(self.images))

    def get_figure(self):
        if self.mpl:
            img_buf = io.BytesIO()
            self.fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
            pil = Image.open(img_buf)
            self.width, self.height = pil.size
            return pil
        else:
            pred_lon, pred_lat, true_lon, true_lat, click_lon, click_lat = self.info
            map = Map(location=BASE_LOCATION, zoom_start=1)
            map._name, map._id = 'visu', '1'

            feature_group = FeatureGroup(name='Ground Truth')
            Marker(
                location=[true_lat, true_lon],
                popup="True location",
                icon_color='red',
            ).add_to(feature_group)
            map.add_child(feature_group)

            icon_square = BeautifyIcon(
                icon_shape='rectangle-dot', 
                border_color='green', 
                border_width=5,
            )
            feature_group_best = FeatureGroup(name='Best Model')
            Marker(
                location=[pred_lat, pred_lon],
                popup="Best Model",
                icon=icon_square,
            ).add_to(feature_group_best)
            GeodesicPolyLine([[true_lat, true_lon], [pred_lat, pred_lon]], color='green').add_to(feature_group_best)
            map.add_child(feature_group_best)

            icon_circle = BeautifyIcon(
                icon_shape='circle-dot', 
                border_color='blue', 
                border_width=5,
            )
            feature_group_user = FeatureGroup(name='User')
            Marker(
                location=[click_lat, click_lon],
                popup="Human",
                icon=icon_circle,
            ).add_to(feature_group_user)
            GeodesicPolyLine([[true_lat, true_lon], [click_lat, click_lon]], color='blue').add_to(feature_group_user)
            map.add_child(feature_group_user)

            map.add_child(LayerControl())

            return map

    def set_clock(self):
        self.time = time.time()

    def get_clock(self):
        return time.time() - self.time

    def mpl_style(self, pred_lon, pred_lat, true_lon, true_lat, click_lon, click_lat):
        if self.mpl:
            self.ax.clear()
            self.ax.set_global()
            self.ax.stock_img()
            self.ax.add_feature(cfeature.COASTLINE)
            self.ax.add_feature(cfeature.BORDERS, linestyle=':')

            self.ax.plot(pred_lon, pred_lat, 'gv', transform=ccrs.Geodetic(), label='model')
            self.ax.plot([true_lon, pred_lon], [true_lat, pred_lat], color='green', linewidth=1, transform=ccrs.Geodetic())
            self.ax.plot(click_lon, click_lat, 'bo', transform=ccrs.Geodetic(), label='user')
            self.ax.plot([true_lon, click_lon], [true_lat, click_lat], color='blue', linewidth=1, transform=ccrs.Geodetic())
            self.ax.plot(true_lon, true_lat, 'rx', transform=ccrs.Geodetic(), label='g.t.')
            legend = self.ax.legend(ncol=3, loc='lower center') #, bbox_to_anchor=(0.5, -0.15), borderaxespad=0.
            legend.get_frame().set_alpha(None)
            self.fig.canvas.draw()
        else:
            self.info = [pred_lon, pred_lat, true_lon, true_lat, click_lon, click_lat]


    def click(self, click_lon, click_lat, country):
        time_elapsed = self.get_clock()
        self.stats['times'].append(time_elapsed)

        # convert click_lon, click_lat to lat, lon (given that you have the borders of the image)
        # click_lon and click_lat is in pixels
        # lon and lat is in degrees
        self.stats['clicked_locations'].append((click_lat, click_lon))
        true_lon, true_lat = self.coordinates[self.index]
        # Get predictions for each model
        model_preds = {}
        for model_name, preds in self.preds.items():
            pred_lon, pred_lat = preds[self.index]
            model_preds[model_name] = (pred_lon, pred_lat)
            
        # Use first model's predictions for visualization
        first_model = list(self.preds.keys())[0]
        pred_lon, pred_lat = model_preds[first_model]

        self.mpl_style(pred_lon, pred_lat, true_lon, true_lat, click_lon, click_lat)

        distance = haversine(true_lat, true_lon, click_lat, click_lon)


        score = geoscore(distance)

        self.stats['scores'].append(score)
        self.stats['distances'].append(distance)
        self.stats['country'].append(int(self.admins[self.index][3] != 'nan' and country == self.admins[self.index][3]))

        df = pd.DataFrame(self.get_model_average('user') + self.get_model_average('models'), columns=['who', 'GeoScore', 'Distance'])
        # Format numbers to 2 significant figures
        df['GeoScore'] = df['GeoScore'].apply(lambda x: float('{:.2g}'.format(x)))
        df['Distance'] = df['Distance'].apply(lambda x: float('{:.2g}'.format(x)))
        df = df.sort_values(by='GeoScore', ascending=False)

        result_text = (
            f"### <span style='color:blue'>GeoScore: {float('{:.2g}'.format(score))}, Distance: {float('{:.2g}'.format(distance))} km <b style='color:blue'>(You)</b></span></br><span style='color:green'>GeoScore: {float('{:.2g}'.format(self.df['score_' + first_model].iloc[self.index]))}, Distance: {float('{:.2g}'.format(self.df['distance_' + first_model].iloc[self.index]))} km <b style='color:green'>({first_model})</b></span>"
        )

        self.cache(self.index, score, distance, (click_lat, click_lon), time_elapsed)
        return self.get_figure(), result_text, df

    def next_image(self):
        # Go to the next image
        self.index += 1
        return self.load_image()

    def get_model_average(self, which, all=False, final=False):
        aux, i = [], self.index
        if which == 'user':
            avg_score = sum(self.stats['scores']) / len(self.stats['scores']) if self.stats['scores'] else 0
            avg_distance = sum(self.stats['distances']) / len(self.stats['distances']) if self.stats['distances'] else 0
            which = 'You'
            if all: 
                avg_city_accuracy = (0 if self.df['city_val'].iloc[:i+1].sum() == 0 else sum(self.stats['city'])/self.df['city_val'].iloc[:i+1].sum())*100
                avg_area_accuracy = (0 if self.df['area_val'].iloc[:i+1].sum() == 0 else sum(self.stats['area'])/self.df['area_val'].iloc[:i+1].sum())*100
                avg_region_accuracy = (0 if self.df['region_val'].iloc[:i+1].sum() == 0 else sum(self.stats['region'])/self.df['region_val'].iloc[:i+1].sum())*100
                aux = [avg_city_accuracy, avg_area_accuracy, avg_region_accuracy]
                return [[which, avg_score, avg_distance] + aux]
            return [[which, avg_score, avg_distance]]
        elif which == 'models':
            return_list = []
            for model in self.models:
                avg_score = np.mean(self.df[['score_'+model]].iloc[:i+1])
                avg_distance = np.mean(self.df[['distance_'+model]].iloc[:i+1])
                
                if all: 
                    aux = [self.df[f'accuracy_city_{model}'].iloc[i], self.df[f'accuracy_area_{model}'].iloc[i], self.df[f'accuracy_region_{model}'].iloc[i]]
                    return_list.append([model, avg_score, avg_distance] + aux)
                else: 
                    return_list.append([model, avg_score, avg_distance])
            return return_list
        else: 
            raise ValueError(f"Invalid argument: {which}")
        
    def update_average_display(self):
        # Calculate the average values
        avg_score = sum(self.stats['scores']) / len(self.stats['scores']) if self.stats['scores'] else 0
        avg_distance = sum(self.stats['distances']) / len(self.stats['distances']) if self.stats['distances'] else 0

        # Update the text box
        return f"GeoScore: {avg_score:.0f}, Distance: {avg_distance:.0f} km"
    
    def finish(self):
        clicks = rg.search(self.stats['clicked_locations'])
        self.stats['city'] = [(int(self.admins[self.index][0] != 'nan' and click['name'] == self.admins[self.index][0])) for click in clicks]
        self.stats['area'] = [(int(self.admins[self.index][1] != 'nan' and click['admin2'] == self.admins[self.index][1])) for click in clicks]
        self.stats['region'] = [(int(self.admins[self.index][2] != 'nan' and click['admin1'] == self.admins[self.index][2])) for click in clicks]
        
        df = pd.DataFrame(self.get_model_average('user') + self.get_model_average('models'), columns=['who', 'GeoScore', 'Distance'])
        # Format numbers to 2 significant figures
        df['GeoScore'] = df['GeoScore'].apply(lambda x: float('{:.2g}'.format(x)))
        df['Distance'] = df['Distance'].apply(lambda x: float('{:.2g}'.format(x)))
        df = df.sort_values(by='GeoScore', ascending=False)
        return df
        
    # Function to save the game state
    def cache(self, index, score, distance, location, time_elapsed):
        order_id = self.order[index] + 1
        os.makedirs(join(JSON_DATASET_DIR, self.tag), exist_ok=True)
        with open(join(JSON_DATASET_DIR, self.tag, f'{order_id}.json'), 'w') as f:
            json.dump({"lat": location[0], "lon": location[1], "time": time_elapsed, "user": self.tag}, f)
            f.write('\n')


if __name__ == "__main__":
    # login with the key from secret
    if 'csv' in os.environ:
        csv_str = os.environ['csv']
        with open(CSV_FILE, 'w') as f:
            f.write(csv_str)
    
    compute_scores(CSV_FILE)
    import gradio as gr
    def click(state, coords):
        if coords == '-1' or state['clicked']:
            return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        lat, lon, country = coords.split(',')
        state['clicked'] = True
        image, text, df = state['engine'].click(float(lon), float(lat), country)
        df = df.sort_values(by='GeoScore', ascending=False)
        kargs = {}
        if not MPL:
            kargs = {'value': empty_map()}
        return gr.update(visible=False, **kargs), gr.update(value=image, visible=True), gr.update(value=text, visible=True), gr.update(value=df, visible=True), gr.update(visible=False), gr.update(visible=True), gr.update()

    def exit_(state):
        if state['engine'].index > 0:
            df = state['engine'].finish()
            return (
                gr.update(visible=False), 
                gr.update(visible=False), 
                gr.update(visible=False), 
                gr.update(value='', visible=True), 
                gr.update(visible=False), 
                gr.update(visible=False), 
                gr.update(value=df, visible=True), 
                gr.update(value="-1", visible=False), 
                gr.update(value="<h1 style='margin-top: 4em;'> AI vs Human Leaderboard on Im2GPS🌍 </h1>", visible=True), 
                gr.update(value="<h3 style='margin-top: 1em;'>Thanks for playing ❤️</h3>", visible=True), 
                gr.update(visible=False),
                gr.update(value="Re-start", visible=True)
            )
        else:
            return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

    def next_(state):
        if state['clicked']:
            if state['engine'].isfinal():
                return exit_(state)
            else:
                image, text = state['engine'].next_image()
                state['clicked'] = False
                kargs = {}
                if not MPL:
                    kargs = {'value': empty_map()}
                return gr.update(value=make_map_(), visible=True), gr.update(visible=False, **kargs), gr.update(value=image), gr.update(value=text, visible=True), gr.update(value='', visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(value="-1"), gr.update(), gr.update(), gr.update(visible=True), gr.update()
        else:
            return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

    def start(state):
        # create a unique random temporary name under CACHE_DIR
        # generate random hex and make sure it doesn't exist under CACHE_DIR
        state['engine'] = Engine(IMAGE_FOLDER, CSV_FILE, MPL, max_images=2)
        state['clicked'] = False
        image, text = state['engine'].load_image()

        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value=image, visible=True),
            gr.update(value=text, visible=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value="<h1>Im2GPS (GPT-4.1)</h1>"),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="-1"),
            gr.update(visible=True),
        )

    with gr.Blocks(css=css, head=space_js) as demo:
        state = gr.State({})
        #rules = gr.Markdown(RULES, visible=True)
        rules = gr.HTML(RULES, visible=True)

        exit_button = gr.Button("Exit", visible=False, elem_id='exit_btn')
        start_button = gr.Button("Start", visible=True, elem_id='start-button')
        with gr.Row():
            map_ = make_map(height=512)
            if MPL:
                results = gr.Image(label='Results', visible=False)
            else:
                results = Folium(height=512, visible=False)
            image_ = gr.Image(label='Image', visible=False, height=512)

        with gr.Row():
            text = gr.Markdown("", visible=False)
            text_count = gr.Markdown("", visible=False)

        with gr.Row():
            select_button = gr.Button("Select", elem_id='latlon_btn', visible=False)
            next_button = gr.Button("Next", visible=False, elem_id='next')
        perf = gr.Dataframe(value=None, visible=False, label='Average Performance (until now)')
        text_end = gr.Markdown("", visible=False)
    
        coords = gr.Textbox(value="-1", label="Latitude, Longitude", visible=False, elem_id='coords-tbox')
        start_button.click(start, inputs=[state], outputs=[map_, results, image_, text_count, text, next_button, rules, state, start_button, coords, select_button])
        select_button.click(click, inputs=[state, coords], outputs=[map_, results, text, perf, select_button, next_button, start_button], js=map_js())
        next_button.click(next_, inputs=[state], outputs=[map_, results, image_, text_count, text, next_button, perf, coords, rules, text_end, select_button, start_button])
        exit_button.click(exit_, inputs=[state], outputs=[map_, results, image_, text_count, text, next_button, perf, coords, rules, text_end, select_button, start_button])

    # local deployment
    #demo.queue().launch(allowed_paths=["custom.ttf", "geoscore.gif"], debug=True)

    # heroku deployment
    port = int(os.environ.get("PORT", 7860))
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=port,
        debug=False,
        allowed_paths=["custom.ttf", "geoscore.gif"]
    )