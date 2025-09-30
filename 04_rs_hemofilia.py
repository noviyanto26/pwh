# 04_rs_hemofilia.py
import os
import io
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Data Rumah Sakit Perawatan Hemofilia",
    page_icon="🏥",
    layout="wide"
)

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

# --- FUNGSI PENGAMBILAN DATA ---

@st.cache_data(ttl="10m")
def load_data_dashboard(_engine: Engine) -> pd.DataFrame:
    """
    Menjalankan query ke database untuk data dashboard utama.
    """
    query = text("SELECT * FROM pwh.rumah_sakit_perawatan_hemofilia ORDER BY no;")
    with _engine.connect() as conn:
        df = pd.read_sql(query, conn)
    for col in ["terdapat_dokter_hematologi", "terdapat_tim_terpadu_hemofilia"]:
        if col in df.columns:
            df[col] = df[col].astype("boolean")
    return df

# --- PERUBAHAN FINAL DI SINI ---
def fetch_data_rekap_rs(engine: Engine) -> pd.DataFrame:
    """
    Mengambil rekap jumlah pasien dari view pwh.v_hospital_summary.
    """
    st.info("🔄 Mengambil data rekapitulasi terbaru dari database...")
    
    # Query disesuaikan dengan skema yang benar, menggunakan tanda kutip ganda
    # untuk nama kolom yang mengandung spasi.
    query = text("""
        SELECT
            "Nama Rumah Sakit" AS nama_rumah_sakit,
            "Jumlah Pasien" AS jumlah_pasien
        FROM pwh.v_hospital_summary
        ORDER BY "Jumlah Pasien" DESC, "Nama Rumah Sakit" ASC;
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        total = int(df["jumlah_pasien"].sum()) if not df.empty else 0
        df["persentase"] = (df["jumlah_pasien"] / total * 100).round(2) if total > 0 else 0.0
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data rekapitulasi dari 'pwh.v_hospital_summary': {e}")
        st.warning("Pastikan view 'pwh.v_hospital_summary' ada dan dapat diakses.")
        return pd.DataFrame()
# --- AKHIR PERUBAHAN ---

# --- FUNGSI UTILITAS & ALIAS (Tidak ada perubahan) ---
def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

def plot_bar(df: pd.DataFrame, label_col: str, value_col: str, title: str, xlabel_text: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14, 8))
    df_sorted = df.sort_values(by=value_col, ascending=True)
    ax.barh(df_sorted[label_col].astype(str), df_sorted[value_col])
    ax.set_title(title, fontsize=16)
    ax.set_xlabel("Jumlah Pasien", fontsize=12)
    ax.set_ylabel(xlabel_text, fontsize=12)
    fig.tight_layout()
    return fig

COL_ALIAS = {
    "no": "No", "provinsi": "Propinsi", "nama_rumah_sakit": "Nama Rumah Sakit",
    "tipe_rs": "Tipe RS", "terdapat_dokter_hematologi": "Terdapat Dokter Hematologi",
    "terdapat_tim_terpadu_hemofilia": "Terdapat Tim Terpadu Hemofilia",
}
DISPLAY_COL_ORDER = [
    "no", "provinsi", "nama_rumah_sakit", "tipe_rs",
    "terdapat_dokter_hematologi", "terdapat_tim_terpadu_hemofilia",
]
def alias_for_display(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in DISPLAY_COL_ORDER if c in df.columns]
    view = df[cols].copy() if cols else df.copy()
    return view.rename(columns={k: v for k, v in COL_ALIAS.items() if k in view.columns})

# --- TAMPILAN APLIKASI (Tidak ada perubahan) ---
st.title("🏥 Dashboard Rumah Sakit Hemofilia")
db_url = _resolve_db_url()
if db_url:
    engine = get_engine(db_url)
    tab1, tab2 = st.tabs(["📊 Dashboard Interaktif", "📈 Rekapitulasi RS Penanganan Pasien"])
    
    with tab1:
        df = load_data_dashboard(engine)
        st.markdown("Gunakan **Filter Data** di bawah untuk menyaring tampilan.")
        st.subheader("🔎 Filter Data")
        c1, c2, c3 = st.columns([1.2, 1, 1])
        with c1:
            provinsi_list = sorted([p for p in df["provinsi"].dropna().unique()])
            provinsi_options = ["Semua Propinsi"] + provinsi_list
            provinsi_pilihan = st.selectbox("Pilih Propinsi", options=provinsi_options, index=0)
        with c2:
            dokter_option = st.selectbox("Ketersediaan Dokter Hematologi", options=["Semua", "Ada", "Tidak Ada", "Data Kosong"], index=0)
        with c3:
            tim_option = st.selectbox("Ketersediaan Tim Terpadu Hemofilia", options=["Semua", "Ada", "Tidak Ada", "Data Kosong"], index=0)

        df_filtered = df.copy()
        if provinsi_pilihan != "Semua Propinsi":
            df_filtered = df_filtered[df_filtered["provinsi"] == provinsi_pilihan]
        if dokter_option == "Ada":
            df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"] == True]
        elif dokter_option == "Tidak Ada":
            df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"] == False]
        elif dokter_option == "Data Kosong":
            df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"].isna()]
        if tim_option == "Ada":
            df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"] == True]
        elif tim_option == "Tidak Ada":
            df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"] == False]
        elif tim_option == "Data Kosong":
            df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"].isna()]

        st.header(f"Tabel Data Rumah Sakit ({len(df_filtered)} data ditemukan)")
        st.dataframe(alias_for_display(df_filtered), use_container_width=True, hide_index=True)
        st.header("Statistik Singkat (dari keseluruhan data)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total RS Tercatat", len(df))
        with col2:
            st.metric("RS Dengan Dokter Hematologi", int((df["terdapat_dokter_hematologi"] == True).sum()))
        with col3:
            st.metric("RS Dengan Tim Terpadu", int((df["terdapat_tim_terpadu_hemofilia"] == True).sum()))
            
    with tab2:
        st.subheader("📈 Rekapitulasi Jumlah Pasien Berdasarkan Rumah Sakit Penanganan")
        df_rekap_raw = fetch_data_rekap_rs(engine)
        if df_rekap_raw.empty:
            st.warning("Tidak ada data penanganan pasien yang dapat ditampilkan.")
        else:
            df_rekap_view = df_rekap_raw.rename(columns={"nama_rumah_sakit": "Nama Rumah Sakit", "jumlah_pasien": "Jumlah Pasien", "persentase": "Persentase (%)"})
            st.dataframe(df_rekap_view.style.format({"Persentase (%)": "{:.2f}"}), use_container_width=True, hide_index=True)
            st.download_button("📥 Download Rekap RS Penanganan (Excel)", data=_to_excel_bytes(df_rekap_view, sheet_name="Rekap_RS_Penanganan"), file_name="rekap_rs_penanganan_pasien.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown("---")
            st.subheader("Visualisasi Data")
            top_20_rs = df_rekap_raw.head(20)
            fig_rekap = plot_bar(df=top_20_rs, label_col="Nama Rumah Sakit", value_col="jumlah_pasien", title="Distribusi Pasien per Rumah Sakit (Top 20)", xlabel_text="Nama Rumah Sakit")
            st.pyplot(fig_rekap)
        st.caption("Sumber data: **pwh.v_hospital_summary**.")
