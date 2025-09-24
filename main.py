# main.py (dengan Indentasi yang Benar)
import streamlit as st
import runpy
from pathlib import Path

# --- Konfigurasi Halaman Utama ---
st.set_page_config(
    page_title="🩸 Dashboard PWH",
    page_icon="🩸",
    layout="wide"
)

# --- Fungsi Autentikasi ---
def check_password():
    """Mengembalikan True jika pengguna sudah diautentikasi."""
    # Cek apakah kunci 'authenticated' sudah ada di session_state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # Jika sudah diautentikasi, langsung kembalikan True
    if st.session_state["authenticated"]:
        return True

    # --- Tampilkan Form Login ---
    st.title("🔐 Halaman Login")
    
    # Ambil daftar username dari st.secrets
    try:
        users = st.secrets["credentials"]["usernames"]
        usernames = list(users.keys())
    except (KeyError, AttributeError):
        st.error("❌ Konfigurasi kredensial di secrets.toml tidak ditemukan.")
        return False
        
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Verifikasi username dan password
        if username in usernames and password == users[username]:
            st.session_state["authenticated"] = True
            st.rerun()  # Muat ulang halaman setelah login berhasil
        else:
            st.error("😕 Username atau password salah.")
    
    return False

# --- Logika Utama Aplikasi ---
# Panggil fungsi check_password. 
# Jika hasilnya False, kode di bawah tidak akan dijalankan.
if not check_password():
    st.stop() # Menghentikan eksekusi script jika belum login

# ===================================================================
# APLIKASI UTAMA (HANYA TAMPIL SETELAH LOGIN BERHASIL)
# ===================================================================

# --- Definisi Menu ---
MENU_ITEMS = {
    "📝 Input Data Pasien": "01_pwh_input.py",
    "📊 Rekapitulasi per Kelompok Usia": "02_rekap_pwh.py",
    "🚻 Rekapitulasi per Jenis Kelamin": "03_rekap_gender.py"
}

# --- Sidebar untuk Navigasi ---
st.sidebar.title("Menu")
st.sidebar.success("Anda berhasil login") # Notifikasi login berhasil
selection = st.sidebar.radio("Pilih Halaman:", list(MENU_ITEMS.keys()))

# Tombol Logout di sidebar
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- Logika untuk Menjalankan Halaman yang Dipilih ---
file_to_run = MENU_ITEMS[selection]
file_path = Path(file_to_run)

if file_path.is_file():
    runpy.run_path(str(file_path))
else:
    st.error(f"File tidak ditemukan: {file_to_run}")
    st.warning("Pastikan file berada di direktori yang sama dengan main.py")
