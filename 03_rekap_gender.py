# 03_rekap_gender.py
import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import matplotlib.pyplot as plt

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Rekapitulasi per Jenis Kelamin", page_icon="🚻", layout="wide")
st.title("🚻 Rekapitulasi Pasien berdasarkan Kategori dan Jenis Kelamin")
st.markdown("Dashboard ini menampilkan rekapitulasi dan grafik pasien berdasarkan jenis hemofilia dan jenis kelamin (Laki-laki/Perempuan).")

# --- KONEKSI DATABASE ---
def _resolve_db_url() -> str:
    """Mencari DATABASE_URL dari st.secrets atau environment variables."""
    try:
        sec = st.secrets.get("DATABASE_URL", "")
        if sec: return sec
    except Exception:
        pass
    env = os.environ.get("DATABASE_URL")
    if env: return env
    
    st.error('DATABASE_URL tidak ditemukan. Mohon atur di `.streamlit/secrets.toml`.')
    return None

@st.cache_resource(show_spinner="Menghubungkan ke database...")
def get_engine(dsn: str) -> Engine:
    """Membuat dan menyimpan koneksi database engine."""
    if not dsn:
        st.stop()
    try:
        engine = create_engine(dsn, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"Gagal terhubung ke database: {e}")
        st.stop()

# --- FUNGSI PENGOLAHAN DATA ---

def fetch_data_for_gender(_engine: Engine) -> pd.DataFrame:
    """
    Mengambil data jenis kelamin pasien dan diagnosis hemofilia.
    """
    st.info("🔄 Mengambil data terbaru dari database...")
    query = text("""
        SELECT
            p.gender AS jenis_kelamin,
            d.hemo_type
        FROM pwh.patients p
        JOIN pwh.hemo_diagnoses d ON p.id = d.patient_id
        WHERE p.gender IS NOT NULL AND d.hemo_type IS NOT NULL;
    """)
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        st.info("Pastikan tabel 'pwh.patients' memiliki kolom 'gender' dan 'pwh.hemo_diagnoses' memiliki kolom 'hemo_type'.")
        return pd.DataFrame()

def map_hemo_type_to_category(hemo_type):
    """Mengelompokkan hemo_type ke kategori yang sesuai."""
    if hemo_type == 'A':
        return 'Hemofilia A'
    if hemo_type == 'B':
        return 'Hemofilia B'
    if hemo_type == 'Other':
        return 'Hemofilia tipe lain'
    if hemo_type == 'vWD':
        return 'VWD'
    return 'Lainnya'

def create_gender_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Membuat tabel rekapitulasi berdasarkan kategori dan jenis kelamin."""
    df['Kategori'] = df['hemo_type'].apply(map_hemo_type_to_category)
    
    # Buat pivot table
    summary = pd.pivot_table(
        df, 
        index='Kategori', 
        columns='jenis_kelamin', 
        aggfunc='size', 
        fill_value=0
    )
    
    # Pastikan kolom Laki-laki dan Perempuan ada
    if 'Laki-laki' not in summary.columns:
        summary['Laki-laki'] = 0
    if 'Perempuan' not in summary.columns:
        summary['Perempuan'] = 0
        
    # Hitung total dan atur urutan
    summary['Total'] = summary.sum(axis=1)
    
    # Atur urutan baris sesuai contoh excel
    category_order = ['Hemofilia A', 'Hemofilia B', 'Hemofilia tipe lain', 'VWD']
    summary = summary.reindex(category_order).fillna(0).astype(int)
    
    return summary[['Laki-laki', 'Perempuan', 'Total']]

def plot_gender_graph(summary_df: pd.DataFrame) -> plt.Figure:
    """Membuat grafik batang dari data rekapitulasi jenis kelamin."""
    plot_df = summary_df.drop(columns='Total', errors='ignore')

    fig, ax = plt.subplots(figsize=(12, 7))
    plot_df.plot(kind='bar', ax=ax)
    
    ax.set_title('Jumlah Pasien berdasarkan Kategori dan Jenis Kelamin', fontsize=16)
    ax.set_xlabel('Kategori Hemofilia', fontsize=12)
    ax.set_ylabel('Jumlah Pasien', fontsize=12)
    plt.xticks(rotation=0)
    ax.legend(title='Jenis Kelamin')
    plt.tight_layout()
    return fig

# --- MAIN APP LOGIC ---
db_url = _resolve_db_url()
engine = get_engine(db_url)
data_df = fetch_data_for_gender(engine)

if data_df.empty:
    st.warning("Tidak ada data yang dapat ditampilkan dari database.")
else:
    rekap_table = create_gender_summary_table(data_df)

    st.subheader("Tabel Rekapitulasi")
    st.dataframe(rekap_table, use_container_width=True)

    csv_data = rekap_table.to_csv(index=True).encode('utf-8')
    st.download_button(
       label="📥 Download Rekapitulasi (CSV)",
       data=csv_data,
       file_name='rekapitulasi_jenis_kelamin.csv',
       mime='text/csv',
    )
    
    st.markdown("---")

    st.subheader("Grafik Visualisasi")
    fig = plot_gender_graph(rekap_table)
    st.pyplot(fig)