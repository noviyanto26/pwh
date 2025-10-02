import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import pydeck as pdk
import requests

# =========================
# KONFIGURASI HALAMAN
# =========================
st.set_page_config(
    page_title="Peta Jumlah Pasien per Kota",
    page_icon="🗺️",
    layout="wide"
)
st.title("🗺️ Peta Jumlah Pasien per Kota (Hemofilia)")

# =========================
# KONEKSI DATABASE
# =========================
# Mengikuti pola di 04_rs_hemofilia.py (st.connection)
conn = st.connection("postgresql", type="sql")

@st.cache_data(ttl="10m", show_spinner="Mengambil rekap RS dari view...")
def load_rekap():
    """
    Mengambil data dari view pwh.v_hospital_summary dengan kolom:
    'Nama Rumah Sakit', 'Jumlah Pasien', 'Kota', 'Propinsi'
    """
    sql = """
        SELECT
            "Nama Rumah Sakit",
            "Jumlah Pasien",
            "Kota",
            "Propinsi"
        FROM pwh.v_hospital_summary
        ORDER BY "Jumlah Pasien" DESC, "Nama Rumah Sakit" ASC;
    """
    df = conn.query(sql)
    # Normalisasi teks untuk konsistensi join/lookup
    for c in ["Kota", "Propinsi"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

# =========================
# SUMBER KOORDINAT LOKAL (Fallback statis)
# =========================
# Beberapa ibukota provinsi + kota besar. Silakan tambah sesuai kebutuhan.
STATIC_CITY_COORDS = {
    # format: ("kota_lower", "propinsi_lower"): (lat, lon)
    ("jakarta", "dki jakarta"): (-6.1754, 106.8272),
    ("jakarta pusat", "dki jakarta"): (-6.1857, 106.8410),
    ("jakarta timur", "dki jakarta"): (-6.2251, 106.9004),
    ("jakarta barat", "dki jakarta"): (-6.1683, 106.7589),
    ("jakarta selatan", "dki jakarta"): (-6.2615, 106.8106),
    ("bekasi", "jawa barat"): (-6.2383, 106.9756),
    ("depok", "jawa barat"): (-6.4025, 106.7942),
    ("bogor", "jawa barat"): (-6.5971, 106.8060),
    ("bandung", "jawa barat"): (-6.9147, 107.6098),
    ("cirebon", "jawa barat"): (-6.7063, 108.5570),
    ("tasikmalaya", "jawa barat"): (-7.3276, 108.2207),
    ("semarang", "jawa tengah"): (-6.9667, 110.4167),
    ("surakarta", "jawa tengah"): (-7.5680, 110.8290),
    ("yogyakarta", "d.i. yogyakarta"): (-7.7972, 110.3688),
    ("surabaya", "jawa timur"): (-7.2575, 112.7521),
    ("malang", "jawa timur"): (-7.9839, 112.6214),
    ("kediri", "jawa timur"): (-7.8178, 112.0114),
    ("sidoarjo", "jawa timur"): (-7.4531, 112.7178),
    ("gresik", "jawa timur"): (-7.1568, 112.6513),
    ("mojokerto", "jawa timur"): (-7.4726, 112.4381),
    ("banyuwangi", "jawa timur"): (-8.2186, 114.3676),
    ("denpasar", "bali"): (-8.6500, 115.2167),
    ("mataram", "nusa tenggara barat"): (-8.5827, 116.1005),
    ("kupang", "nusa tenggara timur"): (-10.1718, 123.6070),
    ("pontianak", "kalimantan barat"): (-0.0263, 109.3425),
    ("palangkaraya", "kalimantan tengah"): (-2.2096, 113.9108),
    ("banjarmasin", "kalimantan selatan"): (-3.3186, 114.5944),
    ("samarinda", "kalimantan timur"): (-0.5022, 117.1536),
    ("balikpapan", "kalimantan timur"): (-1.2379, 116.8523),
    ("manado", "sulawesi utara"): (1.4748, 124.8421),
    ("makassar", "sulawesi selatan"): (-5.1477, 119.4327),
    ("kendari", "sulawesi tenggara"): (-3.9985, 122.5120),
    ("gorontalo", "gorontalo"): (0.5416, 123.0596),
    ("palu", "sulawesi tengah"): (-0.8917, 119.8707),
    ("ambon", "maluku"): (-3.6561, 128.1900),
    ("ternate", "maluku utara"): (0.7906, 127.3848),
    ("jayapura", "papua"): (-2.5916, 140.6689),
    ("merauke", "papua selatan"): (-8.4932, 140.4018),
    ("padang", "sumatera barat"): (-0.9471, 100.4172),
    ("medan", "sumatera utara"): (3.5952, 98.6722),
    ("pekanbaru", "riau"): (0.5071, 101.4478),
    ("palembang", "sumatera selatan"): (-2.9909, 104.7566),
    ("banda aceh", "aceh"): (5.5483, 95.3238),
    ("bandar lampung", "lampung"): (-5.3971, 105.2668),
    ("pangkal pinang", "kep. bangka belitung"): (-2.1291, 106.1096),
    ("tanjung pinang", "kepulauan riau"): (0.9170, 104.4469),
    ("serang", "banten"): (-6.1200, 106.1500),
    ("cilegon", "banten"): (-6.0023, 106.0119),
    ("manokwari", "papua barat"): (-0.8615, 134.0620),
    ("sorong", "papua barat daya"): (-0.8762, 131.2558),
}

# =========================
# OPSI GEOCODING
# =========================
st.sidebar.header("⚙️ Opsi Geocoding & Tampilan")
use_online_geocoding = st.sidebar.toggle(
    "Aktifkan geocoding online (Nominatim/OSM)", value=False,
    help="Jika dinyalakan, kota yang tidak ditemukan di referensi lokal akan dicari via OSM (butuh internet)."
)
heatmap_radius = st.sidebar.slider("Radius Heatmap", min_value=10, max_value=80, value=40, step=5)
min_count = st.sidebar.number_input("Filter minimum jumlah pasien per kota", min_value=0, value=0, step=1)

# =========================
# UTIL GEOCODING
# =========================
@st.cache_data(show_spinner=False)
def load_kota_geo_from_db() -> pd.DataFrame:
    """Mencoba memuat tabel referensi lokal public.kota_geo(kota, propinsi, lat, lon)."""
    try:
        q = "SELECT kota, propinsi, lat, lon FROM public.kota_geo;"
        df_geo = conn.query(q)
        for c in ["kota", "propinsi"]:
            df_geo[c] = df_geo[c].astype(str).str.strip()
        return df_geo
    except Exception:
        return pd.DataFrame(columns=["kota", "propinsi", "lat", "lon"])

@st.cache_data(show_spinner=False)
def nominatim_geocode(city: str, province: str):
    """
    Geocoding via OpenStreetMap Nominatim (opsional).
    Dibungkus cache agar tidak berulang-ulang.
    """
    base = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{city}, {province}, Indonesia",
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "hemofilia-geo/1.0 (contact: youremail@example.com)"}
    try:
        r = requests.get(base, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        j = r.json()
        if isinstance(j, list) and j:
            lat = float(j[0]["lat"])
            lon = float(j[0]["lon"])
            return lat, lon
    except Exception:
        pass
    return None

def lookup_coord(city: str, province: str, df_ref: pd.DataFrame):
    """Urutan lookup: tabel local -> kamus statis -> (opsional) OSM geocode."""
    c = (city or "").strip().lower()
    p = (province or "").strip().lower()

    # 1) referensi lokal
    if not df_ref.empty:
        hit = df_ref[(df_ref["kota"].str.lower() == c) & (df_ref["propinsi"].str.lower() == p)]
        if not hit.empty:
            r = hit.iloc[0]
            return float(r["lat"]), float(r["lon"])

    # 2) kamus statis
    if (c, p) in STATIC_CITY_COORDS:
        return STATIC_CITY_COORDS[(c, p)]

    # 3) Nominatim OSM (opsional)
    if use_online_geocoding:
        res = nominatim_geocode(city, province)
        if res:
            # (Opsional) Anda bisa menambah hasil ke cache lokal (tabel temp) bila mau
            return res

    return None

# =========================
# PROSES DATA & PETA
# =========================
df = load_rekap()

if df.empty:
    st.warning("Data rekap tidak ditemukan. Pastikan view pwh.v_hospital_summary tersedia.")
    st.stop()

# Agregasi ke tingkat kota
grouped = (
    df.groupby(["Kota", "Propinsi"], dropna=False)["Jumlah Pasien"]
      .sum()
      .reset_index()
)
# Filter minimum count
if min_count > 0:
    grouped = grouped[grouped["Jumlah Pasien"] >= min_count].copy()

# Lookup koordinat
geo_ref = load_kota_geo_from_db()
coords = grouped.apply(
    lambda r: lookup_coord(r["Kota"], r["Propinsi"], geo_ref), axis=1
)

grouped["coord"] = coords
grouped = grouped[grouped["coord"].notna()].copy()
grouped[["lat", "lon"]] = pd.DataFrame(grouped["coord"].tolist(), index=grouped.index)

# Tampilkan tabel ringkas
st.subheader(f"📋 Rekap Per Kota (ditemukan koordinat: {len(grouped)}/{len(coords)})")
st.dataframe(
    grouped[["Kota", "Propinsi", "Jumlah Pasien", "lat", "lon"]]
        .sort_values("Jumlah Pasien", ascending=False),
    use_container_width=True, hide_index=True
)

# Map center kasar Indonesia
default_view_state = pdk.ViewState(
    latitude=-2.5, longitude=118.0, zoom=4.2, pitch=0
)

# Layers
heatmap_layer = pdk.Layer(
    "HeatmapLayer",
    data=grouped,
    get_position='[lon, lat]',
    get_weight="Jumlah Pasien",
    radius_pixels=int(heatmap_radius),
)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=grouped,
    get_position='[lon, lat]',
    get_radius="(Math.sqrt(Jumlah Pasien) * 2000)",  # radius proporsional
    pickable=True,
    auto_highlight=True,
)

tooltip = {
    "html": "<b>{Kota}, {Propinsi}</b><br/>Jumlah Pasien: {Jumlah Pasien}",
    "style": {"backgroundColor": "white", "color": "black"}
}

st.subheader("🗺️ Peta Persebaran")
st.pydeck_chart(
    pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",  # gunakan style default; Mapbox token opsional
        initial_view_state=default_view_state,
        layers=[heatmap_layer, scatter_layer],
        tooltip=tooltip,
    )
)

# Unduhan data hasil agregasi + koordinat
st.download_button(
    "📥 Download Data Per Kota (CSV)",
    data=grouped[["Kota", "Propinsi", "Jumlah Pasien", "lat", "lon"]].to_csv(index=False).encode("utf-8"),
    file_name="rekap_pasien_per_kota.csv",
    mime="text/csv",
)

st.caption(
    "Sumber: view **pwh.v_hospital_summary**. Koordinat diambil dari tabel lokal `public.kota_geo` "
    "(jika ada), fallback kamus statis, dan *opsional* geocoding online Nominatim/OSM."
)
