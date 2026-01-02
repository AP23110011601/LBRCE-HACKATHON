import network
import socket
import time
import machine
import dht
import json
import gc
from machine import Pin, ADC

# ==== PINS SETUP ====
soil = ADC(Pin(34))
soil.atten(ADC.ATTN_11DB)
tank = ADC(Pin(35))
tank.atten(ADC.ATTN_11DB)
rain_sensor = ADC(Pin(32))
rain_sensor.atten(ADC.ATTN_11DB)
relay = Pin(27, Pin.OUT)
relay.value(1)  # Initially OFF
dht_sensor = dht.DHT11(Pin(4))

# ==== SYSTEM VARIABLES ====
system_mode = "auto"  # auto/manual
dry_threshold = 3000   # ADC value when dry
wet_threshold = 1500   # ADC value when wet
tank_low_threshold = 3000  # Empty tank ADC
tank_full_threshold = 800  # Full tank ADC
current_language = "en"
operation_logs = []
predicted_crop = "paddy"
RAIN_THRESHOLD = 50  # Adjust based on your sensor

# ==== WIFI CONFIG ====
WIFI_SSID = "kusuma"
WIFI_PASSWORD = "12345678"

# ==== SEASON DETECTION ====
def get_season():
    """Determine season based on month with Rabi/Kharif classification"""
    month = time.localtime()[1]
    
    if month in [10, 11, 12, 1, 2]:
        season_type = "rabi"
        if month in [10, 11]:
            return "rabi_sowing", season_type
        elif month in [12, 1]:
            return "rabi_growing", season_type
        else:
            return "rabi_harvest", season_type
            
    elif month in [6, 7, 8, 9]:
        season_type = "kharif"
        if month in [6, 7]:
            return "kharif_sowing", season_type
        elif month in [8, 9]:
            return "kharif_growing", season_type
        else:
            return "kharif_harvest", season_type
            
    else:
        season_type = "zaid"
        return "zaid", season_type

# ==== TRANSLATIONS ====
TRANSLATIONS = {
    "en": {
        "title": "Smart Crop Predictor",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "soil_moisture": "Soil Moisture",
        "rain_status": "Rain Status",
        "tank_level": "Tank Level",
        "irrigation": "Pump",
        "refresh": "Refresh",
        "toggle_pump": "Toggle Pump",
        "change_mode": "Mode",
        "force_water": "Force Water",
        "manual_water": "Manual Water",
        "stop_water": "Stop Water",
        "status_good": "Good",
        "status_warn": "Warning",
        "status_crit": "Critical",
        "suggestion": "Suggestion:",
        "logs": "Logs",
        "clear_logs": "Clear",
        "rain_detected": "Rain detected - Pump OFF",
        "no_rain": "No rain",
        "soil_dry": "Soil dry - irrigation needed",
        "soil_wet": "Soil wet - stop irrigation",
        "tank_empty": "Tank empty! Refill needed",
        "normal": "Normal conditions",
        "predicted_crop": "PREDICTED CROP",
        "best_crop": "Best Crop:",
        "crop_score": "Suitability:",
        "auto_mode": "Auto Prediction",
        "current_season": "Season:",
        "language": "Language",
        "crops": {
            "paddy": {"name": "Rice", "emoji": "🌾", "desc": "Kharif crop", "season_type": "kharif"},
            "wheat": {"name": "Wheat", "emoji": "🌾", "desc": "Rabi crop", "season_type": "rabi"},
            "maize": {"name": "Maize", "emoji": "🌽", "desc": "Kharif/Rabi", "season_type": "both"},
            "vegetables": {"name": "Vegetables", "emoji": "🥦", "desc": "All seasons", "season_type": "all"},
            "cotton": {"name": "Cotton", "emoji": "🧵", "desc": "Kharif crop", "season_type": "kharif"},
            "millets": {"name": "Millets", "emoji": "🌾", "desc": "Kharif crop", "season_type": "kharif"},
            "groundnut": {"name": "Groundnut", "emoji": "🥜", "desc": "Kharif crop", "season_type": "kharif"},
            "sugarcane": {"name": "Sugarcane", "emoji": "🎋", "desc": "Year-round", "season_type": "all"}
        },
        "seasons": {
            "rabi_sowing": "🌱 Rabi (Sowing)",
            "rabi_growing": "🌾 Rabi (Growing)",
            "rabi_harvest": "📦 Rabi (Harvest)",
            "kharif_sowing": "🌱 Kharif (Sowing)",
            "kharif_growing": "🌾 Kharif (Growing)", 
            "kharif_harvest": "📦 Kharif (Harvest)",
            "zaid": "☀️ Zaid (Summer)"
        }
    },
    "hi": {
        "title": "स्मार्ट फसल भविष्यवक्ता",
        "temperature": "तापमान",
        "humidity": "नमी",
        "soil_moisture": "मिट्टी नमी",
        "rain_status": "वर्षा स्थिति",
        "tank_level": "टैंक स्तर",
        "irrigation": "पम्प",
        "refresh": "रिफ्रेश",
        "toggle_pump": "पम्प टॉगल",
        "change_mode": "मोड",
        "force_water": "जबरन पानी",
        "manual_water": "मैन्युअल पानी",
        "stop_water": "पानी रोको",
        "status_good": "अच्छा",
        "status_warn": "चेतावनी",
        "status_crit": "गंभीर",
        "suggestion": "सलाह:",
        "logs": "लॉग",
        "clear_logs": "साफ",
        "rain_detected": "बारिश - पम्प बंद",
        "no_rain": "बारिश नहीं",
        "soil_dry": "मिट्टी सूखी - सिंचाई चाहिए",
        "soil_wet": "मिट्टी गीली - सिंचाई बंद",
        "tank_empty": "टैंक खाली! भरें",
        "normal": "सामान्य",
        "predicted_crop": "भविष्यवाणी फसल",
        "best_crop": "सर्वोत्तम फसल:",
        "crop_score": "उपयुक्तता:",
        "auto_mode": "स्वचालित भविष्यवाणी",
        "current_season": "मौसम:",
        "language": "भाषा",
        "crops": {
            "paddy": {"name": "धान", "emoji": "🌾", "desc": "खरीफ फसल", "season_type": "kharif"},
            "wheat": {"name": "गेहूं", "emoji": "🌾", "desc": "रबी फसल", "season_type": "rabi"},
            "maize": {"name": "मक्का", "emoji": "🌽", "desc": "खरीफ/रबी", "season_type": "both"},
            "vegetables": {"name": "सब्जियां", "emoji": "🥦", "desc": "सभी मौसम", "season_type": "all"},
            "cotton": {"name": "कपास", "emoji": "🧵", "desc": "खरीफ फसल", "season_type": "kharif"},
            "millets": {"name": "मोटे अनाज", "emoji": "🌾", "desc": "खरीफ फसल", "season_type": "kharif"},
            "groundnut": {"name": "मूंगफली", "emoji": "🥜", "desc": "खरीफ फसल", "season_type": "kharif"},
            "sugarcane": {"name": "गन्ना", "emoji": "🎋", "desc": "पूरे साल", "season_type": "all"}
        },
        "seasons": {
            "rabi_sowing": "🌱 रबी (बुवाई)",
            "rabi_growing": "🌾 रबी (बढ़ रहा)",
            "rabi_harvest": "📦 रबी (कटाई)",
            "kharif_sowing": "🌱 खरीफ (बुवाई)",
            "kharif_growing": "🌾 खरीफ (बढ़ रहा)", 
            "kharif_harvest": "📦 खरीफ (कटाई)",
            "zaid": "☀️ जायद (गर्मी)"
        }
    },
    "te": {
        "title": "స్మార్ట్ పంట ఊహించేందుకు",
        "temperature": "ఉష్ణోగ్రత",
        "humidity": "తేమ",
        "soil_moisture": "నేల తేమ",
        "rain_status": "వర్షం స్థితి",
        "tank_level": "ట్యాంక్ స్థాయి",
        "irrigation": "పంపు",
        "refresh": "రిఫ్రెష్",
        "toggle_pump": "పంపు మార్పు",
        "change_mode": "మోడ్",
        "force_water": "నీరు బలం",
        "manual_water": "మాన్యువల్ నీరు",
        "stop_water": "నీరు ఆపండి",
        "status_good": "మంచిది",
        "status_warn": "హెచ్చరిక",
        "status_crit": "క్లిష్టం",
        "suggestion": "సలహా:",
        "logs": "లాగ్‌లు",
        "clear_logs": "క్లియర్",
        "rain_detected": "వర్షం - పంపు ఆఫ్",
        "no_rain": "వర్షం లేదు",
        "soil_dry": "నేల పొడి - నీరు కావాలి",
        "soil_wet": "నేల తడి - నీరు ఆపండి",
        "tank_empty": "ట్యాంక్ ఖాళీ! నింపండి",
        "normal": "సాధారణం",
        "predicted_crop": "ఊహించిన పంట",
        "best_crop": "ఉత్తమ పంట:",
        "crop_score": "సరిపడుతుంది:",
        "auto_mode": "స్వయంచాలకంగా ఊహించు",
        "current_season": "ఋతువు:",
        "language": "భాష",
        "crops": {
            "paddy": {"name": "వరి", "emoji": "🌾", "desc": "ఖరీఫ్ పంట", "season_type": "kharif"},
            "wheat": {"name": "గోధుమ", "emoji": "🌾", "desc": "రబీ పంట", "season_type": "rabi"},
            "maize": {"name": "మొక్కజొన్న", "emoji": "🌽", "desc": "ఖరీఫ్/రబీ", "season_type": "both"},
            "vegetables": {"name": "కూరగాయలు", "emoji": "🥦", "desc": "అన్ని ఋతువులు", "season_type": "all"},
            "cotton": {"name": "పత్తి", "emoji": "🧵", "desc": "ఖరీఫ్ పంట", "season_type": "kharif"},
            "millets": {"name": "చిన్నధాన్యాలు", "emoji": "🌾", "desc": "ఖరీఫ్ పంట", "season_type": "kharif"},
            "groundnut": {"name": "వేరుశనగ", "emoji": "🥜", "desc": "ఖరీఫ్ పంట", "season_type": "kharif"},
            "sugarcane": {"name": "చెరకు", "emoji": "🎋", "desc": "సంవత్సరం పొడవునా", "season_type": "all"}
        },
        "seasons": {
            "rabi_sowing": "🌱 రబీ (విత్తడం)",
            "rabi_growing": "🌾 రబీ (పెరుగుతోంది)",
            "rabi_harvest": "📦 రబీ (కోత)",
            "kharif_sowing": "🌱 ఖరీఫ్ (విత్తడం)",
            "kharif_growing": "🌾 ఖరీఫ్ (పెరుగుతోంది)", 
            "kharif_harvest": "📦 ఖరీఫ్ (కోత)",
            "zaid": "☀️ జైద్ (వేసవి)"
        }
    }
}

def get_translation(key):
    """Get translation for current language"""
    keys = key.split('.')
    value = TRANSLATIONS.get(current_language, TRANSLATIONS["en"])
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return key
    return value if value is not None else key

def read_sensors():
    """Read all sensor values"""
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
    except:
        temperature = 28
        humidity = 65
    
    soil_value = soil.read()
    tank_value = tank.read()
    rain_value = rain_sensor.read()
    
    # Rain detection
    is_raining = rain_value < RAIN_THRESHOLD
    
    # Soil moisture percentage calculation
    if soil_value >= dry_threshold:
        soil_percent = 0
    elif soil_value <= wet_threshold:
        soil_percent = 100
    else:
        soil_percent = 100 - ((soil_value - wet_threshold) / (dry_threshold - wet_threshold) * 100)
    soil_percent = int(max(0, min(100, soil_percent)))
    
    # Tank level percentage calculation
    if tank_value >= tank_low_threshold:
        tank_percent = 0
    elif tank_value <= tank_full_threshold:
        tank_percent = 100
    else:
        tank_percent = 100 - ((tank_value - tank_full_threshold) / (tank_low_threshold - tank_full_threshold) * 100)
    tank_percent = int(max(0, min(100, tank_percent)))
    
    return {
        'temp': temperature,
        'humidity': humidity,
        'soil_value': soil_value,
        'tank_value': tank_value,
        'rain_value': rain_value,
        'soil_percent': soil_percent,
        'tank_percent': tank_percent,
        'rain': 0 if is_raining else 1,
        'relay': relay.value()
    }

def predict_best_crop(data):
    """Predict the best crop based on sensor data AND season"""
    temp = data['temp']
    moisture = data['soil_percent']
    rain = data['rain']
    season, season_type = get_season()
    
    crops = [
        ("paddy", "Rice", 20, 35, 70, 95, "kharif"),
        ("wheat", "Wheat", 10, 25, 40, 70, "rabi"),
        ("maize", "Maize", 15, 30, 50, 80, "both"),
        ("vegetables", "Vegetables", 15, 30, 60, 85, "all"),
        ("cotton", "Cotton", 20, 35, 45, 75, "kharif"),
        ("millets", "Millets", 20, 40, 30, 65, "kharif"),
        ("groundnut", "Groundnut", 22, 35, 40, 70, "kharif"),
        ("sugarcane", "Sugarcane", 20, 35, 65, 90, "all")
    ]
    
    crop_scores = []
    for crop_id, crop_name, min_temp, max_temp, min_moisture, max_moisture, crop_season in crops:
        score = 0
        
        # Season compatibility (40% weight)
        if crop_season == "all":
            score += 40
        elif crop_season == "both" and season_type in ["rabi", "kharif"]:
            score += 40
        elif crop_season == season_type:
            score += 40
        elif crop_season == "kharif" and season_type == "zaid":
            score += 20
        elif crop_season == "rabi" and season_type == "zaid":
            score += 15
        else:
            score += 5
        
        # Temperature score (30% weight)
        if min_temp <= temp <= max_temp:
            score += 30
        elif temp < min_temp:
            temp_diff = min_temp - temp
            if temp_diff <= 5:
                score += 20
            elif temp_diff <= 10:
                score += 10
            else:
                score += 5
        else:
            temp_diff = temp - max_temp
            if temp_diff <= 5:
                score += 20
            elif temp_diff <= 10:
                score += 10
            else:
                score += 5
        
        # Moisture score (30% weight)
        if min_moisture <= moisture <= max_moisture:
            score += 30
        elif moisture < min_moisture:
            if min_moisture - moisture <= 10:
                score += 20
            elif min_moisture - moisture <= 20:
                score += 10
            else:
                score += 5
        else:
            if moisture - max_moisture <= 10:
                score += 20
            elif moisture - max_moisture <= 20:
                score += 10
            else:
                score += 5
        
        crop_scores.append((crop_id, crop_name, score))
    
    crop_scores.sort(key=lambda x: x[2], reverse=True)
    best_crop_id = crop_scores[0][0]
    best_score = crop_scores[0][2]
    
    score_percent = min(100, int(best_score))
    if score_percent >= 80:
        rating = "⭐⭐⭐ Excellent" if current_language == "en" else "⭐⭐⭐ उत्तम" if current_language == "hi" else "⭐⭐⭐ అద్భుతం"
        color = "#10b981"
    elif score_percent >= 60:
        rating = "⭐⭐ Good" if current_language == "en" else "⭐⭐ अच्छा" if current_language == "hi" else "⭐⭐ మంచిది"
        color = "#3b82f6"
    elif score_percent >= 40:
        rating = "⭐ Fair" if current_language == "en" else "⭐ ठीक" if current_language == "hi" else "⭐ సరిపోతుంది"
        color = "#f59e0b"
    else:
        rating = "⭕ Poor" if current_language == "en" else "⭕ खराब" if current_language == "hi" else "⭕ పేలవం"
        color = "#ef4444"
    
    return best_crop_id, score_percent, rating, color, crop_scores

def analyze_conditions():
    """Analyze sensor data and provide advice"""
    data = read_sensors()
    
    if data['rain'] == 0:
        if relay.value() == 0 and system_mode == "auto":
            relay.value(1)
            add_log(get_translation("rain_detected"))
        return {"advice": get_translation("rain_detected"), "status": "warn"}
    
    if data['tank_percent'] < 20:
        if relay.value() == 0:
            relay.value(1)
            add_log(get_translation("tank_empty"))
        return {"advice": get_translation("tank_empty"), "status": "crit"}
    
    if system_mode == "auto":
        if data['soil_percent'] < 30:
            if data['tank_percent'] > 20:
                if relay.value() == 1:
                    relay.value(0)
                    add_log(get_translation("soil_dry"))
                return {"advice": get_translation("soil_dry"), "status": "warn"}
        
        elif data['soil_percent'] > 80:
            if relay.value() == 0:
                relay.value(1)
                add_log(get_translation("soil_wet"))
            return {"advice": get_translation("soil_wet"), "status": "good"}
    
    return {"advice": get_translation("normal"), "status": "good"}

def add_log(msg):
    """Add log entry"""
    t = time.localtime()
    timestamp = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    operation_logs.insert(0, f"[{timestamp}] {msg}")
    if len(operation_logs) > 10:
        operation_logs.pop()

def connect_wifi():
    """Connect to WiFi"""
    print("Connecting to WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    max_wait = 20
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        time.sleep(1)
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"✅ Connected! IP: {ip}")
        return ip
    else:
        print("❌ WiFi failed. Creating Access Point...")
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid='SmartFarm-AP', password='12345678')
        time.sleep(2)
        ip = ap.ifconfig()[0]
        print(f"📡 AP IP: {ip}")
        return ip

def generate_html():
    """Generate HTML page"""
    data = read_sensors()
    analysis = analyze_conditions()
    season, season_type = get_season()
    
    best_crop_id, score_percent, rating, rating_color, all_scores = predict_best_crop(data)
    
    crop_info = get_translation(f"crops.{best_crop_id}")
    if isinstance(crop_info, dict):
        crop_name = crop_info.get("name", best_crop_id)
        crop_emoji = crop_info.get("emoji", "🌱")
        crop_desc = crop_info.get("desc", "")
    else:
        crop_name = best_crop_id
        crop_emoji = "🌱"
        crop_desc = ""
    
    status_colors = {
        "good": "#10b981",
        "warn": "#f59e0b", 
        "crit": "#ef4444"
    }
    
    rain_text = "🌧️ " + ("RAINING" if current_language == "en" else "बारिश" if current_language == "hi" else "వర్షం") if data['rain'] == 0 else "☀️ " + ("NO RAIN" if current_language == "en" else "बारिश नहीं" if current_language == "hi" else "వర్షం లేదు")
    rain_color = "#3b82f6" if data['rain'] == 0 else "#f59e0b"
    
    pump_text = "💧 " + ("ON" if current_language == "en" else "चालू" if current_language == "hi" else "ఆన్") if data['relay'] == 0 else "❌ " + ("OFF" if current_language == "en" else "बंद" if current_language == "hi" else "ఆఫ్")
    pump_color = "#ef4444" if data['relay'] == 0 else "#10b981"
    
    status_text = get_translation(f"status_{analysis['status']}")
    
    season_trans = get_translation(f"seasons.{season}")
    
    logs_html = ""
    for log in operation_logs[:8]:
        logs_html += f'<div class="log-entry">{log}</div>'
    
    crop_table = ""
    for crop_id, crop_name_disp, score in all_scores[:4]:
        crop_emoji_local = get_translation(f"crops.{crop_id}.emoji") if isinstance(get_translation(f"crops.{crop_id}"), dict) else "🌱"
        crop_display = get_translation(f"crops.{crop_id}.name") if isinstance(get_translation(f"crops.{crop_id}"), dict) else crop_name_disp
        bar_width = min(100, int(score))
        bar_color = "#10b981" if score >= 70 else "#3b82f6" if score >= 50 else "#f59e0b" if score >= 30 else "#ef4444"
        
        crop_table += f"""
        <div class="crop-row">
            <div style="flex: 1; font-weight: bold;">{crop_emoji_local} {crop_display}</div>
            <div style="width: 60px; text-align: right; font-weight: bold; color:{bar_color};">{int(score)}%</div>
            <div style="width: 100px;">
                <div style="height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                    <div style="width: {bar_width}%; height: 100%; background: {bar_color};"></div>
                </div>
            </div>
        </div>"""
    
    manual_alert = f'<div class="alert">⚠️ {get_translation("manual_water")}: {get_translation("auto_mode") if system_mode == "manual" else ""}</div>' if system_mode == "manual" else ''
    tank_alert = '<div class="alert">⚠️ ' + ("Low water level!" if current_language == "en" else "कम पानी!" if current_language == "hi" else "నీటి స్థాయి తక్కువ!") + '</div>' if data['tank_percent'] < 20 else ''
    
    # Language selection
    lang_options = ""
    for lang_code, lang_name in [("en", "English"), ("hi", "हिन्दी"), ("te", "తెలుగు")]:
        selected = "selected" if current_language == lang_code else ""
        lang_options += f'<option value="{lang_code}" {selected}>{lang_name}</option>'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{get_translation("title")}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 15px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
        }}
        .header {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .sensor-grid {{ 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 12px; 
            margin-bottom: 15px;
        }}
        .sensor-card {{ 
            background: white; 
            padding: 15px; 
            border-radius: 10px; 
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .value {{ 
            font-size: 24px; 
            font-weight: bold; 
            margin: 5px 0;
        }}
        .label {{ 
            font-size: 12px; 
            color: #6b7280;
            font-weight: bold;
        }}
        .prediction-card {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            border: 3px solid {rating_color};
        }}
        .controls {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .btn-row {{ 
            display: flex; 
            flex-wrap: wrap; 
            gap: 10px; 
            margin: 10px 0;
        }}
        .btn {{ 
            flex: 1; 
            background: #10b981; 
            color: white; 
            border: none; 
            padding: 12px; 
            border-radius: 8px; 
            cursor: pointer;
            font-weight: bold;
            min-width: 120px;
        }}
        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        .btn-danger {{ background: #ef4444; }}
        .btn-warn {{ background: #f59e0b; }}
        .btn-blue {{ background: #3b82f6; }}
        .btn-purple {{ background: #8b5cf6; }}
        .logs {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .log-entry {{ 
            padding: 8px; 
            border-bottom: 1px solid #e5e7eb; 
            font-size: 12px;
            font-family: monospace;
        }}
        .status {{ 
            padding: 6px 15px; 
            border-radius: 20px; 
            font-size: 14px; 
            font-weight: bold;
            display: inline-block;
        }}
        .crop-comparison {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .crop-row {{ 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            padding: 10px 0;
            border-bottom: 1px solid #f3f4f6;
        }}
        .advice-box {{ 
            background: {status_colors[analysis['status']]}20; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 15px 0;
            border-left: 5px solid {status_colors[analysis['status']]};
        }}
        .alert {{ 
            background: #fef3c7; 
            border-left: 5px solid #f59e0b; 
            padding: 10px; 
            border-radius: 5px; 
            margin: 10px 0;
            font-size: 12px;
        }}
        select {{
            padding: 8px 15px;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
            background: white;
            font-weight: bold;
            margin: 5px;
        }}
        .loading {{
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 20px 40px;
            border-radius: 10px;
            z-index: 1000;
            font-size: 18px;
        }}
        @media (max-width: 600px) {{
            .sensor-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .btn {{ min-width: 100px; }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">⏳ Processing...</div>
    <div class="container">
        <div class="header">
            <h1 style="margin:0;color:#2e7d32;">{get_translation("title")}</h1>
            <div style="color:#6b7280;margin:5px 0;">{season_type.upper()} {get_translation("current_season")} • {get_translation("auto_mode")}</div>
            <div style="margin-top:10px;">
                <select id="languageSelect" onchange="changeLanguage(this.value)">
                    {lang_options}
                </select>
                <div class="status" style="background:#8b5cf6;color:white;display:inline-block;margin-left:10px;">
                    {get_translation("current_season")} {season_trans}
                </div>
            </div>
        </div>
        
        <div class="prediction-card">
            <div class="label" style="color:#6b7280;font-size:14px;">{get_translation("predicted_crop")}</div>
            <div style="font-size:48px;margin:10px 0;">{crop_emoji}</div>
            <div style="font-size:28px;font-weight:bold;color:#1f2937;margin:5px 0;">{crop_name}</div>
            <div style="color:#6b7280;margin:10px 0;font-size:14px;">{crop_desc}</div>
            <div style="font-size:20px;font-weight:bold;color:{rating_color};margin:10px 0;">{rating} ({score_percent}%)</div>
            <div style="font-size:12px;color:#9ca3af;">{get_translation("auto_mode")}</div>
        </div>
        
        <div class="sensor-grid">
            <div class="sensor-card">
                <div class="label">{get_translation("temperature")}</div>
                <div class="value" style="color:#ef4444;">{data['temp']}°C</div>
            </div>
            <div class="sensor-card">
                <div class="label">{get_translation("humidity")}</div>
                <div class="value" style="color:#3b82f6;">{data['humidity']}%</div>
            </div>
            <div class="sensor-card">
                <div class="label">{get_translation("soil_moisture")}</div>
                <div class="value" style="color:#10b981;">{data['soil_percent']}%</div>
            </div>
            <div class="sensor-card">
                <div class="label">{get_translation("tank_level")}</div>
                <div class="value" style="color:#8b5cf6;">{data['tank_percent']}%</div>
                {tank_alert}
            </div>
            <div class="sensor-card">
                <div class="label">{get_translation("rain_status")}</div>
                <div class="value" style="color:{rain_color};">{rain_text}</div>
                <div style="font-size:11px;color:#9ca3af;">ADC: {data['rain_value']}</div>
            </div>
            <div class="sensor-card">
                <div class="label">{get_translation("irrigation")}</div>
                <div class="value" style="color:{pump_color};">{pump_text}</div>
                <div style="font-size:11px;color:#9ca3af;">{system_mode.upper()} {get_translation("change_mode")}</div>
            </div>
        </div>
        
        <div class="advice-box">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: bold; color:#1f2937;">
                    {get_translation("suggestion")} {analysis['advice']}
                </div>
                <div class="status" style="background:{status_colors[analysis['status']]};color:white;">
                    {status_text}
                </div>
            </div>
            {manual_alert}
        </div>
        
        <div class="crop-comparison">
            <h3 style="margin:0 0 15px 0;color:#1f2937;">🌱 {get_translation("best_crop")}</h3>
            {crop_table}
            <div style="text-align:center;margin-top:10px;font-size:12px;color:#6b7280;">
                {get_translation("crop_score")} {score_percent}%
            </div>
        </div>
        
        <div class="controls">
            <div class="btn-row">
                <button class="btn" onclick="refreshData()">{get_translation("refresh")} 🔄</button>
                <button class="btn {'btn-danger' if data['relay']==0 else 'btn-blue'}" onclick="handleAction('pump')">
                    {get_translation("toggle_pump")} ({'STOP' if data['relay']==0 else 'START'})
                </button>
                <button class="btn {'btn-warn' if system_mode=='auto' else 'btn-purple'}" onclick="handleAction('mode')">
                    {get_translation("change_mode")} ({system_mode.upper()})
                </button>
            </div>
            <div class="btn-row">
                <button class="btn btn-blue" onclick="handleAction('force')">{get_translation("force_water")} (5s)</button>
                <button class="btn {'btn-danger' if data['relay']==0 else ''}" onclick="handleAction('stop')">{get_translation("stop_water")}</button>
            </div>
        </div>
        
        <div class="logs">
            <h3 style="margin:0 0 15px 0;color:#1f2937;">📝 {get_translation("logs")}</h3>
            <div style="max-height:200px;overflow-y:auto;">
                {logs_html}
            </div>
            <button class="btn btn-danger" onclick="handleAction('clear')" style="margin-top:15px;width:100%;">{get_translation("clear_logs")}</button>
        </div>
        
        <div style="text-align:center;margin-top:20px;font-size:12px;color:white;">
            <div>{get_translation("title")} • {season_type.upper()} {get_translation("current_season")} • {get_translation("auto_mode")}</div>
            <div>{get_translation("language")}: {current_language.upper()} • Auto-refresh: 5s</div>
        </div>
    </div>
    
    <script>
        let isProcessing = false;
        let autoRefreshTimer = null;
        
        function showLoading() {{
            document.getElementById('loading').style.display = 'block';
            document.querySelectorAll('.btn').forEach(btn => btn.disabled = true);
        }}
        
        function hideLoading() {{
            document.getElementById('loading').style.display = 'none';
            document.querySelectorAll('.btn').forEach(btn => btn.disabled = false);
        }}
        
        function changeLanguage(lang) {{
            if (isProcessing) return;
            isProcessing = true;
            showLoading();
            
            fetch('/lang?l=' + lang)
                .then(response => response.text())
                .then(() => {{
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 400);
                }})
                .catch(err => {{
                    console.error('Error:', err);
                    hideLoading();
                    isProcessing = false;
                    alert('Error changing language');
                }});
        }}
        
        function refreshData() {{
            if (isProcessing) return;
            showLoading();
            window.location.href = '/';
        }}
        
        function handleAction(action) {{
            if (isProcessing) return;
            isProcessing = true;
            showLoading();
            
            // Stop auto-refresh during action
            if (autoRefreshTimer) {{
                clearTimeout(autoRefreshTimer);
            }}
            
            fetch('/control?a=' + action)
                .then(response => response.text())
                .then(data => {{
                    console.log('Action completed:', data);
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 500);
                }})
                .catch(err => {{
                    console.error('Error:', err);
                    hideLoading();
                    isProcessing = false;
                    startAutoRefresh();
                    alert('Error: ' + err);
                }});
        }}
        
        function startAutoRefresh() {{
            // Auto-refresh every 5 seconds
            if (autoRefreshTimer) {{
                clearTimeout(autoRefreshTimer);
            }}
            autoRefreshTimer = setTimeout(() => {{
                if (!isProcessing) {{
                    window.location.href = '/';
                }}
            }}, 5000);
        }}
        
        // Start auto-refresh on page load
        window.addEventListener('load', function() {{
            startAutoRefresh();
        }});
    </script>
</body>
</html>"""
    
    return html

def start_server():
    """Start web server"""
    print("\n" + "="*50)
    print("Starting Smart Crop Prediction System...")
    print("="*50)
    
    ip = connect_wifi()
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(5)
    
    print(f"\n✅ Server started!")
    print(f"📱 Open browser: http://{ip}")
    season, season_type = get_season()
    print(f"🌾 Current season: {season_type.upper()}")
    print(f"🌐 Languages: English, Hindi, Telugu")
    print("="*50)
    
    add_log("System started - Multi-language support")
    
    while True:
        conn = None
        try:
            conn, addr = s.accept()
            request = conn.recv(1024).decode()
            
            if not request:
                conn.close()
                continue
            
            lines = request.split('\r\n')
            if not lines:
                conn.close()
                continue
            
            req_line = lines[0]
            parts = req_line.split()
            if len(parts) < 2:
                conn.close()
                continue
            
            method = parts[0]
            path = parts[1]
            
            if method == 'GET':
                if path == '/' or '/dashboard' in path:
                    html = generate_html()
                    conn.send('HTTP/1.1 200 OK\r\n')
                    conn.send('Content-Type: text/html\r\n')
                    conn.send('Connection: close\r\n\r\n')
                    conn.sendall(html)
                
                elif '/control' in path:
                    if 'a=pump' in path:
                        relay.value(1 if relay.value() == 0 else 0)
                        log_msg = "Pump ON" if relay.value() == 0 else "Pump OFF"
                        add_log(log_msg)
                    
                    elif 'a=mode' in path:
                        global system_mode
                        system_mode = "manual" if system_mode == "auto" else "auto"
                        add_log(f"Mode: {system_mode}")
                        if system_mode == "auto":
                            analyze_conditions()
                    
                    elif 'a=force' in path:
                        relay.value(0)
                        add_log("Force water ON (5s)")
                        def auto_off():
                            time.sleep(5)
                            if relay.value() == 0:
                                relay.value(1)
                                add_log("Force water OFF")
                        import _thread
                        _thread.start_new_thread(auto_off, ())
                    
                    elif 'a=stop' in path:
                        relay.value(1)
                        add_log("Water STOP")
                    
                    elif 'a=clear' in path:
                        global operation_logs
                        operation_logs = []
                        add_log("Logs cleared")
                    
                    conn.send('HTTP/1.1 200 OK\r\n')
                    conn.send('Content-Type: text/plain\r\n')
                    conn.send('Connection: close\r\n\r\n')
                    conn.send('OK')
                
                elif '/lang' in path:
                    global current_language
                    
                    if 'l=en' in path:
                        current_language = "en"
                        add_log("Language: English")
                    elif 'l=hi' in path:
                        current_language = "hi"
                        add_log("Language: Hindi")
                    elif 'l=te' in path:
                        current_language = "te"
                        add_log("Language: Telugu")
                    
                    conn.send('HTTP/1.1 200 OK\r\n')
                    conn.send('Content-Type: text/plain\r\n')
                    conn.send('Connection: close\r\n\r\n')
                    conn.send('OK')
                
                elif '/data' in path:
                    data = read_sensors()
                    analysis = analyze_conditions()
                    best_crop_id, score_percent, rating, rating_color, all_scores = predict_best_crop(data)
                    
                    json_data = json.dumps({
                        'temp': data['temp'],
                        'humidity': data['humidity'],
                        'soil': data['soil_percent'],
                        'tank': data['tank_percent'],
                        'rain': data['rain'],
                        'pump': data['relay'],
                        'mode': system_mode,
                        'season': get_season()[0],
                        'predicted_crop': best_crop_id,
                        'crop_score': score_percent
                    })
                    
                    conn.send('HTTP/1.1 200 OK\r\n')
                    conn.send('Content-Type: application/json\r\n')
                    conn.send('Connection: close\r\n\r\n')
                    conn.send(json_data)
                
                else:
                    conn.send('HTTP/1.1 404 Not Found\r\n')
                    conn.send('Content-Type: text/plain\r\n')
                    conn.send('Connection: close\r\n\r\n')
                    conn.send('404 Not Found')
            
            else:
                conn.send('HTTP/1.1 405 Method Not Allowed\r\n')
                conn.send('Connection: close\r\n\r\n')
            
            if conn:
                conn.close()
            
            if system_mode == "auto":
                analyze_conditions()
            
            gc.collect()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            s.close()
            break
        except Exception as e:
            print(f"Error: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            gc.collect()
            time.sleep(0.1)

# ==== MAIN ====
gc.collect()
start_server()
