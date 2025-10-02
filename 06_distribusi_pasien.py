# 06_distribusi_pasien.py — Peta Jumlah Pasien per Kota (Hemofilia)
import os
import pandas as pd
import streamlit as st
import pydeck as pdk
import requests
from typing import Callable, Optional
from sqlalchemy import create_engine, text

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
# UTIL KONEKSI (dual-mode)
# =========================
def _build_query_runner() -> Callable[[str], pd.DataFrame]:
    """
    Mengembalikan fungsi run_query(sql) -> DataFrame.
    Prioritas:
      1) st.connection("postgresql", type="sql")
      2) SQLAlchemy via st.secrets["DATABASE_URL"] / env DATABASE_URL
    """
    # 1) Streamlit connection
    try:
        conn = st.connection("postgresql", type="sql")
        def _run_query_streamlit(sql: str) -> pd.DataFrame:
            return conn.query(sql)
        # uji ringan
        _ = _run_query_streamlit("SELECT 1 as ok;")
        return _run_query_streamlit
    except Exception:
        pass

    # 2) SQLAlchemy (DATABASE_URL)
    db_url = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
    if not db_url:
        st.error("❌ Koneksi DB tidak dikonfigurasi. Set 'connections.postgresql' di secrets.toml "
                 "atau 'DATABASE_URL' di secrets.")
        st.stop()
    engine = create_engine(db_url, pool_pre_ping=True)

    def _run_query_engine(sql: str) -> pd.DataFrame:
        with engine.connect() as con:
            return pd.read_sql(text(sql), con)
    # uji ringan
    _ = _run_query_engine("SELECT 1 as ok;")
    return _run_query_engine

run_query = _build_query_runner()

# =========================
# DATA REKAP
# =========================
@st.cache_data(ttl="10m", show_spinner="Mengambil rekap RS dari view...")
def load_rekap() -> pd.DataFrame:
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
    df = run_query(sql)
    for c in ["Kota", "Propinsi"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

# =========================
# SUMBER KOORDINAT LOKAL (Fallback statis)
# =========================
STATIC_CITY_COORDS = {
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
# definisi
@st.cache_data(show_spinner=False)
def load_kota_geo_from_db(_run: Callable[[str], pd.DataFrame]) -> pd.DataFrame:
    try:
        q = "SELECT kota, propinsi, lat, lon FROM public.kota_geo;"
        df_geo = _run(q)
        for c in ["kota", "propinsi"]:
            df_geo[c] = df_geo[c].astype(str).str.strip()
        return df_geo
    except Exception:
        return pd.DataFrame(columns=["kota", "propinsi", "lat", "lon"])

# pemanggilan
geo_ref = load_kota_geo_from_db(run_query)

@st.cache_data(show_spinner=False)
def nominatim_geocode(city: str, province: str) -> Optional[tuple]:
    """Geocoding via OpenStreetMap Nominatim (opsional)."""
    base = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{city}, {province}, Indonesia", "format": "json", "limit": 1}
    headers = {"User-Agent": "hemofilia-geo/1.0 (contact: youremail@example.com)"}
    try:
        r = requests.get(base, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        j = r.json()
        if isinstance(j, list) and j:
            return float(j[0]["lat"]), float(j[0]["lon"])
    except Exception:
        pass
    return None

def lookup_coord(city: str, province: str, df_ref: pd.DataFrame) -> Optional[tuple]:
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
            return res

    return None

def _is_valid_coord(v) -> bool:
    """Valid jika tuple/list 2 elemen dan keduanya non-null."""
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(pd.notna(v))

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

# Lookup koordinat & validasi
geo_ref = load_kota_geo_from_db(run_query)
grouped["coord"] = grouped.apply(
    lambda r: lookup_coord(r["Kota"], r["Propinsi"], geo_ref), axis=1
)

valid_mask = grouped["coord"].apply(_is_valid_coord)
grouped_valid = grouped[valid_mask].copy()

# expand ke lat/lon (aman karena sudah tervalidasi)
latlon = grouped_valid["coord"].apply(pd.Series)
latlon.columns = ["lat", "lon"]
grouped_valid = pd.concat([grouped_valid.drop(columns=["coord"]), latlon], axis=1)

# pastikan float & drop NaN
grouped_valid["lat"] = pd.to_numeric(grouped_valid["lat"], errors="coerce")
grouped_valid["lon"] = pd.to_numeric(grouped_valid["lon"], errors="coerce")
grouped_valid = grouped_valid.dropna(subset=["lat", "lon"])

# Tampilkan tabel ringkas
st.subheader(f"📋 Rekap Per Kota (koordinat valid: {len(grouped_valid)}/{len(grouped)})")
st.dataframe(
    grouped_valid[["Kota", "Propinsi", "Jumlah Pasien", "lat", "lon"]]
        .sort_values("Jumlah Pasien", ascending=False),
    use_container_width=True, hide_index=True
)

# Map center kasar Indonesia
default_view_state = pdk.ViewState(latitude=-2.5, longitude=118.0, zoom=4.2, pitch=0)

# Layers
heatmap_layer = pdk.Layer(
    "HeatmapLayer",
    data=grouped_valid,
    get_position='[lon, lat]',
    get_weight="Jumlah Pasien",
    radius_pixels=int(heatmap_radius),
)
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=grouped_valid,
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
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=default_view_state,
        layers=[heatmap_layer, scatter_layer],
        tooltip=tooltip,
    )
)

# Unduhan data hasil agregasi + koordinat
st.download_button(
    "📥 Download Data Per Kota (CSV)",
    data=grouped_valid[["Kota", "Propinsi", "Jumlah Pasien", "lat", "lon"]].to_csv(index=False).encode("utf-8"),
    file_name="rekap_pasien_per_kota.csv",
    mime="text/csv",
)

st.caption(
    "Sumber: view **pwh.v_hospital_summary**. Koordinat diambil dari tabel lokal `public.kota_geo` "
    "(jika ada), fallback kamus statis, dan *opsional* geocoding online Nominatim/OSM."
)
