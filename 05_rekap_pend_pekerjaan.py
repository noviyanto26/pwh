# 04_rs_hemofilia.py
import streamlit as st
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Data Rumah Sakit Perawatan Hemofilia",
    page_icon="🏥",
    layout="wide"
)

# --- KONEKSI DAN FUNGSI PENGAMBILAN DATA ---

# Inisialisasi koneksi ke database PostgreSQL (diambil dari .streamlit/secrets.toml)
conn = st.connection("postgresql", type="sql")

@st.cache_data(ttl="10m")
def load_data():
    """
    Menjalankan query ke database dan mengembalikan hasilnya sebagai DataFrame.
    """
    query = "SELECT * FROM pwh.rumah_sakit_perawatan_hemofilia ORDER BY no;"
    df = conn.query(query)

    # Pastikan kolom boolean bertipe benar (True/False/NA)
    for col in ["terdapat_dokter_hematologi", "terdapat_tim_terpadu_hemofilia"]:
        if col in df.columns:
            df[col] = df[col].astype("boolean")
    return df

# --- ALIAS KOL0M UNTUK TAMPILAN ---
COL_ALIAS = {
    "no": "No",
    "provinsi": "Propinsi",
    "nama_rumah_sakit": "Nama Rumah Sakit",
    "tipe_rs": "Tipe RS",
    "terdapat_dokter_hematologi": "Terdapat Dokter Hematologi",
    "terdapat_tim_terpadu_hemofilia": "Terdapat Tim Terpadu Hemofilia",
}

DISPLAY_COL_ORDER = [
    "no",
    "provinsi",
    "nama_rumah_sakit",
    "tipe_rs",
    "terdapat_dokter_hematologi",
    "terdapat_tim_terpadu_hemofilia",
]

def alias_for_display(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in DISPLAY_COL_ORDER if c in df.columns]
    view = df[cols].copy() if cols else df.copy()
    return view.rename(columns={k: v for k, v in COL_ALIAS.items() if k in view.columns})

# --- TAMPILAN APLIKASI ---
st.title("🏥 Dashboard Data Rumah Sakit Perawatan Hemofilia")
st.markdown(
    "Gunakan **Filter Data** di bawah untuk menyaring tampilan. "
    "Secara default, semua rumah sakit ditampilkan."
)

try:
    df = load_data()

    # ================== FILTER DI HALAMAN UTAMA ==================
    st.subheader("🔎 Filter Data")

    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        # Pilih Propinsi: selectbox (single) dengan default "Semua Propinsi"
        provinsi_list = sorted([p for p in df["provinsi"].dropna().unique()])
        provinsi_options = ["Semua Propinsi"] + provinsi_list
        provinsi_pilihan = st.selectbox("Pilih Propinsi", options=provinsi_options, index=0)

    with c2:
        dokter_option = st.selectbox(
            "Ketersediaan Dokter Hematologi",
            options=["Semua", "Ada", "Tidak Ada", "Data Kosong"],
            index=0,
        )

    with c3:
        tim_option = st.selectbox(
            "Ketersediaan Tim Terpadu Hemofilia",
            options=["Semua", "Ada", "Tidak Ada", "Data Kosong"],
            index=0,
        )

    # ================== PROSES FILTER ==================
    df_filtered = df.copy()

    # Filter Propinsi (hanya jika bukan "Semua Propinsi")
    if provinsi_pilihan != "Semua Propinsi":
        df_filtered = df_filtered[df_filtered["provinsi"] == provinsi_pilihan]

    # Filter Dokter Hematologi
    if dokter_option == "Ada":
        df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"] == True]
    elif dokter_option == "Tidak Ada":
        df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"] == False]
    elif dokter_option == "Data Kosong":
        df_filtered = df_filtered[df_filtered["terdapat_dokter_hematologi"].isna()]

    # Filter Tim Terpadu Hemofilia
    if tim_option == "Ada":
        df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"] == True]
    elif tim_option == "Tidak Ada":
        df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"] == False]
    elif tim_option == "Data Kosong":
        df_filtered = df_filtered[df_filtered["terdapat_tim_terpadu_hemofilia"].isna()]

    # ================== TABEL & STATISTIK ==================
    st.header(f"Tabel Data Rumah Sakit ({len(df_filtered)} data ditemukan)")
    st.dataframe(
        alias_for_display(df_filtered),
        use_container_width=True,
        hide_index=True
    )

    st.header("Statistik Singkat")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total RS Tercatat", len(df))
    with col2:
        st.metric("RS Dengan Dokter Hematologi", int((df["terdapat_dokter_hematologi"] == True).sum()))
    with col3:
        st.metric("RS Dengan Tim Terpadu", int((df["terdapat_tim_terpadu_hemofilia"] == True).sum()))

except Exception as e:
    st.error(f"Gagal terhubung ke database atau mengambil data: {e}")
    st.info(
        "Pastikan file `.streamlit/secrets.toml` sudah dikonfigurasi dengan benar "
        "dan database PostgreSQL Anda sedang berjalan."
    )
