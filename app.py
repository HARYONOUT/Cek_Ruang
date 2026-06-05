import streamlit as st
import pandas as pd
import sqlite3
import os
import re

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Rekap Data Peserta Ujian UT", layout="wide", page_icon="📊")

DB_NAME = "data_ujian_ut.db"

# --- FUNGSI BANTUAN DATABASE & FILE ---
def get_conn():
    return sqlite3.connect(DB_NAME)

def load_file(file):
    if file is None:
        return None
    try:
        file.seek(0)
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"Gagal membaca file {file.name}: {e}")
    return None

def load_table(table_name):
    try:
        conn = get_conn()
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# --- VALIDASI KOLOM WAJIB ---
def validate_master_wilayah(df):
    required = ['id_wilayah', 'nama_kabupaten']
    return all(col in df.columns for col in required)

def validate_master_sekolah(df):
    required = ['id_sekolah', 'nama_sekolah', 'id_wilayah']
    return all(col in df.columns for col in required)

def validate_master_ruang(df):
    required = ['id_sekolah', 'Ruang', 'nama_ruang', 'kapasitas']
    if not all(col in df.columns for col in required):
        return False
    try:
        pd.to_numeric(df['kapasitas'], errors='raise')
        return True
    except:
        return False

def validate_peserta(df):
    # Minimal kolom yang diperlukan untuk laporan
    required = ['kode_tuo', 'ruang', 'kode_sesi', 'tgl_ujian']
    return all(col in df.columns for col in required)

# --- FUNGSI MEMBUAT TABEL DATA PESERTA JIKA BELUM ADA ---
def create_data_peserta_table_if_not_exists(conn, sample_df=None):
    """
    Membuat tabel data_peserta jika belum ada.
    Jika sample_df diberikan, kolomnya akan disesuaikan (tapi minimal ada kolom wajib).
    """
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_peserta'")
    if not c.fetchone():
        # Jika sample_df ada, gunakan kolomnya untuk membuat tabel
        if sample_df is not None:
            cols = []
            for col in sample_df.columns:
                # Tentukan tipe data sederhana (semua TEXT untuk kemudahan)
                cols.append(f'"{col}" TEXT')
            create_sql = f"CREATE TABLE data_peserta ({', '.join(cols)})"
            c.execute(create_sql)
        else:
            # Buat tabel minimal dengan kolom wajib
            c.execute('''
                CREATE TABLE data_peserta (
                    kode_tuo TEXT,
                    ruang TEXT,
                    kode_sesi TEXT,
                    tgl_ujian TEXT,
                    nama_tuo TEXT,
                    nama_wilayah_ujian TEXT
                )
            ''')
        conn.commit()

# --- NAVIGASI SIDEBAR ---
st.sidebar.title("📌 Navigasi Menu")
menu = st.sidebar.radio("Pilih Menu:", ["📊 Dasbor Laporan", "⚙️ Pengaturan Data"])
st.sidebar.divider()
st.sidebar.info("Gunakan menu **Pengaturan Data** untuk mengunggah/mengupdate data ke Database. Gunakan **Dasbor Laporan** untuk melihat rekapitulasi.")

# ==========================================
# MENU 2: PENGATURAN DATA (UPLOAD & SIMPAN)
# ==========================================
if menu == "⚙️ Pengaturan Data":
    st.title("⚙️ Pengaturan & Basis Data")
    st.markdown("Unggah dan simpan data ke dalam sistem. Data akan tersimpan permanen di database lokal (SQLite) sehingga Anda tidak perlu mengunggah ulang setiap membuka aplikasi.")
    
    st.header("1. Data Master")
    col1, col2, col3 = st.columns(3)
    
    # 1. Master Wilayah
    with col1:
        st.subheader("🗺️ Master Wilayah")
        f_wil = st.file_uploader("Upload File Master Wilayah", type=['csv','xls','xlsx'], key='f_wil')
        if f_wil and st.button("💾 Simpan Wilayah"):
            with st.spinner("Menyimpan..."):
                df = load_file(f_wil)
                if df is not None and validate_master_wilayah(df):
                    conn = get_conn()
                    df.to_sql("master_wilayah", conn, if_exists="replace", index=False)
                    conn.close()
                    st.success("✅ Master Wilayah tersimpan!")
                else:
                    st.error("❌ File tidak valid. Pastikan kolom: id_wilayah, nama_kabupaten.")
                    
    # 2. Master Sekolah
    with col2:
        st.subheader("🏫 Master Sekolah")
        f_sek = st.file_uploader("Upload File Master Sekolah", type=['csv','xls','xlsx'], key='f_sek')
        if f_sek and st.button("💾 Simpan Sekolah"):
            with st.spinner("Menyimpan..."):
                df = load_file(f_sek)
                if df is not None and validate_master_sekolah(df):
                    conn = get_conn()
                    df.to_sql("master_sekolah", conn, if_exists="replace", index=False)
                    conn.close()
                    st.success("✅ Master Sekolah tersimpan!")
                else:
                    st.error("❌ File tidak valid. Pastikan kolom: id_sekolah, nama_sekolah, id_wilayah.")
                    
    # 3. Master Ruang
    with col3:
        st.subheader("🚪 Master Ruang")
        f_rng = st.file_uploader("Upload File Master Ruang", type=['csv','xls','xlsx'], key='f_rng')
        if f_rng and st.button("💾 Simpan Ruang"):
            with st.spinner("Menyimpan..."):
                df = load_file(f_rng)
                if df is not None and validate_master_ruang(df):
                    df['id_sekolah'] = df['id_sekolah'].astype(str)
                    df['Ruang'] = df['Ruang'].astype(str)
                    df['kapasitas'] = pd.to_numeric(df['kapasitas'], errors='coerce').fillna(0).astype(int)
                    conn = get_conn()
                    df.to_sql("master_ruang", conn, if_exists="replace", index=False)
                    conn.close()
                    st.success("✅ Master Ruang tersimpan!")
                else:
                    st.error("❌ File tidak valid. Pastikan kolom: id_sekolah, Ruang, nama_ruang, kapasitas (angka).")

    st.divider()
    
    # 4. Data Peserta
    st.header("2. Data Peserta Ujian")
    st.info("💡 **Tips Update:** Anda bisa mengunggah semua file sekaligus (saat awal), atau mengunggah **1 file saja untuk update** sekolah tertentu. Sistem akan otomatis mengganti data lama pada sekolah tersebut dengan data dari file yang baru Anda unggah.")
    
    f_peserta = st.file_uploader("Unggah File Peserta (Bisa pilih satu atau banyak file sekaligus)", type=['csv','xls','xlsx'], accept_multiple_files=True, key='f_pes')
    
    col_pes_1, col_pes_2 = st.columns([3, 1])
    
    with col_pes_1:
        if f_peserta and st.button("💾 Simpan / Update Data Peserta Sekolah"):
            success_count = 0
            with st.spinner("Memproses dan memperbarui data peserta ke database..."):
                conn = get_conn()
                c = conn.cursor()
                c.execute("BEGIN TRANSACTION")
                try:
                    for file in f_peserta:
                        df_p = load_file(file)
                        if df_p is not None and validate_peserta(df_p):
                            # Bersihkan kode_tuo, ruang
                            df_p['kode_tuo'] = df_p['kode_tuo'].astype(str).str.split('.').str[0].str.strip()
                            df_p['ruang'] = df_p['ruang'].astype(str).str.split('.').str[0].str.strip()
                            
                            # Konversi kode_sesi ke integer lalu string (1,2,3...)
                            df_p['kode_sesi'] = pd.to_numeric(df_p['kode_sesi'], errors='coerce').fillna(0).astype(int).astype(str)
                            
                            # Konversi tgl_ujian ke format YYYY-MM-DD
                            df_p['tgl_ujian'] = pd.to_datetime(df_p['tgl_ujian'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
                            
                            # Hapus kolom Unnamed
                            df_p = df_p.loc[:, ~df_p.columns.str.contains('^Unnamed')]
                            
                            # **Perbaikan: Buat tabel jika belum ada (gunakan df_p sebagai acuan kolom)**
                            create_data_peserta_table_if_not_exists(conn, sample_df=df_p)
                            
                            # Sinkronisasi kolom: pastikan df_p hanya memiliki kolom yang ada di database
                            c.execute("PRAGMA table_info(data_peserta)")
                            db_cols = [col[1] for col in c.fetchall()]
                            # Hanya ambil kolom yang ada di df_p dan juga di database
                            valid_cols = [col for col in df_p.columns if col in db_cols]
                            df_p = df_p[valid_cols]
                            
                            # Hapus data lama untuk kode_tuo yang ada di file ini
                            kodes_tuo = df_p['kode_tuo'].unique()
                            for k in kodes_tuo:
                                c.execute("DELETE FROM data_peserta WHERE kode_tuo = ?", (str(k),))
                            
                            # Insert data baru
                            df_p.to_sql("data_peserta", conn, if_exists="append", index=False)
                            success_count += 1
                        else:
                            st.warning(f"File {file.name} dilewati. Pastikan kolom: kode_tuo, ruang, kode_sesi, tgl_ujian.")
                    conn.commit()
                    st.success(f"✅ Berhasil menyimpan/mengupdate data dari {success_count} file sekolah ke Database!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"Terjadi error: {e}. Transaksi dibatalkan.")
                finally:
                    conn.close()

    with col_pes_2:
        if st.button("🗑️ Reset Semua Data Peserta"):
            conn = get_conn()
            conn.execute("DROP TABLE IF EXISTS data_peserta")
            conn.commit()
            conn.close()
            st.success("✅ Tabel data peserta berhasil dikosongkan.")
            st.rerun()

    st.divider()

    # 5. Pengaturan Ujian Khusus (2 Sesi)
    st.header("3. Pengaturan Ujian Khusus (S2 / UKT - 2 Sesi)")
    st.info("Gunakan pengaturan ini untuk mendaftarkan jadwal sekolah dan **RUANG** yang spesifik menyelenggarakan ujian hanya dengan **2 Sesi** (seperti S2 atau UKT). Laporan kapasitas otomatis akan menyesuaikan menjadi 2 sesi pada ruang dan tanggal tersebut.")

    df_wil = load_table("master_wilayah")
    df_sek = load_table("master_sekolah")
    df_rng_master = load_table("master_ruang")

    if not df_wil.empty and not df_sek.empty and not df_rng_master.empty:
        if not validate_master_wilayah(df_wil):
            st.error("❌ Data Master Wilayah tidak valid (id_wilayah atau nama_kabupaten).")
        elif not validate_master_sekolah(df_sek):
            st.error("❌ Data Master Sekolah tidak valid.")
        elif not validate_master_ruang(df_rng_master):
            st.error("❌ Data Master Ruang tidak valid.")
        else:
            col_w, col_s, col_r, col_t = st.columns(4)
            with col_w:
                pilih_w = st.selectbox("1. Pilih Wilayah", df_wil['nama_kabupaten'].unique())
                id_w = df_wil[df_wil['nama_kabupaten'] == pilih_w]['id_wilayah'].iloc[0]
                
            with col_s:
                df_sek_filter = df_sek[df_sek['id_wilayah'].astype(str) == str(id_w)]
                if not df_sek_filter.empty:
                    pilih_s_nama = st.selectbox("2. Pilih Sekolah (TUO)", df_sek_filter['nama_sekolah'].unique())
                    id_s = df_sek_filter[df_sek_filter['nama_sekolah'] == pilih_s_nama]['id_sekolah'].iloc[0]
                else:
                    st.warning("Belum ada sekolah.")
                    id_s = None
            
            with col_r:
                if id_s:
                    df_rng_filter = df_rng_master[df_rng_master['id_sekolah'].astype(str) == str(id_s)].copy()
                    if not df_rng_filter.empty:
                        df_rng_filter['label_ruang'] = df_rng_filter['Ruang'].astype(str) + " - " + df_rng_filter['nama_ruang'].astype(str)
                        pilih_r_label = st.selectbox("3. Pilih Ruang Khusus", df_rng_filter['label_ruang'].unique())
                        id_r = df_rng_filter[df_rng_filter['label_ruang'] == pilih_r_label]['Ruang'].iloc[0]
                    else:
                        st.warning("Belum ada ruang.")
                        id_r = None
                else:
                    st.selectbox("3. Pilih Ruang Khusus", [])
                    id_r = None
                    
            with col_t:
                tgl_khusus = st.date_input("4. Tanggal Ujian Khusus")

            if st.button("➕ Tambah Jadwal Ujian Khusus") and id_s and id_r:
                conn = get_conn()
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS jadwal_khusus (id_sekolah TEXT, ruang TEXT, tanggal TEXT)")
                c.execute("PRAGMA table_info(jadwal_khusus)")
                cols = [col[1] for col in c.fetchall()]
                if 'ruang' not in cols:
                    c.execute("DROP TABLE jadwal_khusus")
                    c.execute("CREATE TABLE jadwal_khusus (id_sekolah TEXT, ruang TEXT, tanggal TEXT)")
                
                c.execute("SELECT * FROM jadwal_khusus WHERE id_sekolah=? AND ruang=? AND tanggal=?", 
                          (str(id_s), str(id_r), str(tgl_khusus)))
                if c.fetchone() is None:
                    c.execute("INSERT INTO jadwal_khusus (id_sekolah, ruang, tanggal) VALUES (?, ?, ?)", 
                              (str(id_s), str(id_r), str(tgl_khusus)))
                    conn.commit()
                    st.success(f"✅ Jadwal khusus {pilih_s_nama} (Ruang {id_r}) pada tanggal {tgl_khusus} berhasil ditambahkan!")
                else:
                    st.warning("⚠️ Jadwal ruang tersebut sudah ada dalam daftar!")
                conn.close()
                st.rerun() 

            df_jk = load_table("jadwal_khusus")
            if not df_jk.empty:
                if 'ruang' not in df_jk.columns:
                    df_jk['ruang'] = "-"
                st.subheader("Daftar Ruang Ujian Khusus (2 Sesi) Saat Ini:")
                df_jk_tampil = pd.merge(df_jk, df_sek[['id_sekolah', 'nama_sekolah']], on='id_sekolah', how='left')
                df_jk_tampil = pd.merge(df_jk_tampil, df_rng_master[['id_sekolah', 'Ruang', 'nama_ruang']], 
                                        left_on=['id_sekolah', 'ruang'], right_on=['id_sekolah', 'Ruang'], how='left')
                df_jk_tampil = df_jk_tampil[['id_sekolah', 'nama_sekolah', 'ruang', 'nama_ruang', 'tanggal']]
                df_jk_tampil.rename(columns={'id_sekolah': 'Kode TUO', 'nama_sekolah': 'Nama Sekolah', 
                                             'ruang': 'No Ruang', 'nama_ruang': 'Nama Ruang', 'tanggal': 'Tanggal Ujian Khusus'}, inplace=True)
                st.dataframe(df_jk_tampil, use_container_width=True, hide_index=True)
                
                if st.button("🗑️ Hapus Semua Jadwal Khusus"):
                    conn = get_conn()
                    conn.execute("DROP TABLE IF EXISTS jadwal_khusus")
                    conn.commit()
                    conn.close()
                    st.success("Semua jadwal khusus telah dihapus.")
                    st.rerun()
    else:
        st.warning("💡 Harap unggah dan simpan Data Master Wilayah, Sekolah, dan Ruang terlebih dahulu untuk menggunakan fitur ini.")

# ==========================================
# MENU 1: DASBOR LAPORAN
# ==========================================
elif menu == "📊 Dasbor Laporan":
    st.title("📊 Dasbor Rekapitulasi Peserta Ujian Online UT Semarang")
    
    with st.spinner("Mengambil data dari database..."):
        df_wilayah = load_table("master_wilayah")
        df_sekolah = load_table("master_sekolah")
        df_ruang = load_table("master_ruang")
        df_peserta = load_table("data_peserta")
        df_jadwal_khusus = load_table("jadwal_khusus")
    
    if df_peserta.empty or df_ruang.empty:
        st.warning("⚠️ Data belum lengkap di Database. Silakan masuk ke menu **Pengaturan Data** (di sidebar kiri) untuk mengunggah dan menyimpan file Master & Peserta.")
    else:
        # Standarisasi tipe data
        df_ruang['id_sekolah'] = df_ruang['id_sekolah'].astype(str)
        df_ruang['Ruang_std'] = df_ruang['Ruang'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
        df_ruang['kapasitas'] = pd.to_numeric(df_ruang['kapasitas'], errors='coerce').fillna(0).astype(int)
        
        df_peserta['kode_tuo'] = df_peserta['kode_tuo'].astype(str)
        df_peserta['ruang_std'] = df_peserta['ruang'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
        
        # Parsing kode_sesi yang benar
        df_peserta['kode_sesi_str'] = pd.to_numeric(df_peserta['kode_sesi'], errors='coerce').fillna(0).astype(int).astype(str)
        
        df_peserta['tgl_ujian'] = pd.to_datetime(df_peserta['tgl_ujian'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_peserta = df_peserta.dropna(subset=['tgl_ujian'])
        
        # --- BANGUN DATA WILAYAH UNTUK SETIAP PESERTA (JOIN) ---
        if not df_sekolah.empty and not df_wilayah.empty:
            df_peserta = df_peserta.merge(df_sekolah[['id_sekolah', 'id_wilayah']], left_on='kode_tuo', right_on='id_sekolah', how='left')
            df_peserta = df_peserta.merge(df_wilayah[['id_wilayah', 'nama_kabupaten']], on='id_wilayah', how='left')
            if 'nama_wilayah_ujian' not in df_peserta.columns:
                df_peserta['nama_wilayah_ujian'] = df_peserta['nama_kabupaten'].fillna('Tidak diketahui')
        else:
            if 'nama_wilayah_ujian' not in df_peserta.columns:
                df_peserta['nama_wilayah_ujian'] = 'Tidak diketahui'
        
        # Tab laporan
        tab1, tab2 = st.tabs(["🗺️ Rekap per Wilayah", "🏫 Detail per Sekolah & Ruang"])
        
        # --- TAB 1: REKAP WILAYAH ---
        with tab1:
            st.header("Rekapitulasi Berdasarkan Wilayah")
            list_wilayah = sorted(df_peserta['nama_wilayah_ujian'].dropna().unique().tolist())
            pilih_wilayah = st.selectbox("🔍 Pilih Wilayah:", ["-- Semua Wilayah --"] + list_wilayah)
            
            if pilih_wilayah == "-- Semua Wilayah --":
                df_filter_wilayah = df_peserta
            else:
                df_filter_wilayah = df_peserta[df_peserta['nama_wilayah_ujian'] == pilih_wilayah]
            
            if not df_filter_wilayah.empty:
                rekap_wilayah = df_filter_wilayah.groupby(['kode_tuo', 'nama_tuo', 'tgl_ujian']).size().reset_index(name='Total Kursi Digunakan')
                rekap_wilayah.rename(columns={'kode_tuo': 'Kode TUO', 'nama_tuo': 'Nama Sekolah / TUO', 'tgl_ujian': 'Tanggal Ujian'}, inplace=True)
                rekap_wilayah = rekap_wilayah.sort_values(by=['Tanggal Ujian', 'Nama Sekolah / TUO'])
                st.dataframe(rekap_wilayah, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                col1.metric("Total Sekolah Menggelar Ujian", len(rekap_wilayah['Kode TUO'].unique()))
                col2.metric("Total Kursi Terpakai", rekap_wilayah['Total Kursi Digunakan'].sum())
            else:
                st.info("Tidak ada data peserta untuk wilayah ini.")
        
        # --- TAB 2: DETAIL RUANG ---
        with tab2:
            st.header("Detail Keterisian Ruang per Sekolah")
            
            if df_wilayah.empty or df_sekolah.empty:
                st.warning("Data master wilayah/sekolah tidak lengkap. Silakan unggah ulang.")
            else:
                col_w_laporan, col_s_laporan = st.columns(2)
                list_wilayah_master = sorted(df_wilayah['nama_kabupaten'].dropna().astype(str).unique().tolist())
                
                with col_w_laporan:
                    pilih_wilayah_laporan = st.selectbox("🗺️ Pilih Wilayah:", list_wilayah_master, key="wilayah_laporan")
                    id_w_laporan = df_wilayah[df_wilayah['nama_kabupaten'] == pilih_wilayah_laporan]['id_wilayah'].iloc[0]
                
                with col_s_laporan:
                    df_sek_filter_laporan = df_sekolah[df_sekolah['id_wilayah'].astype(str) == str(id_w_laporan)]
                    if not df_sek_filter_laporan.empty:
                        list_sekolah_filter = sorted(df_sek_filter_laporan['nama_sekolah'].dropna().astype(str).unique().tolist())
                        pilih_sekolah = st.selectbox("🏫 Pilih Sekolah (TUO):", list_sekolah_filter, key="sekolah_laporan")
                    else:
                        st.warning("Belum ada sekolah di wilayah ini.")
                        pilih_sekolah = None
                
                if pilih_sekolah:
                    kode_sekolah_terpilih = df_sekolah[df_sekolah['nama_sekolah'] == pilih_sekolah]['id_sekolah'].iloc[0]
                    df_filter_sekolah = df_peserta[df_peserta['kode_tuo'].astype(str) == str(kode_sekolah_terpilih)]
                    
                    list_tanggal = sorted(df_filter_sekolah['tgl_ujian'].dropna().unique().tolist())
                    if list_tanggal:
                        pilih_tanggal = st.selectbox("📅 Pilih Tanggal Ujian:", list_tanggal)
                        df_detail = df_filter_sekolah[df_filter_sekolah['tgl_ujian'] == pilih_tanggal]
                    else:
                        pilih_tanggal = None
                        df_detail = pd.DataFrame()
                        st.info("Belum ada data peserta (tanggal ujian) untuk sekolah ini.")
                    
                    ruang_sekolah_ini = df_ruang[df_ruang['id_sekolah'] == str(kode_sekolah_terpilih)].copy()
                    
                    if not ruang_sekolah_ini.empty and pilih_tanggal:
                        # Tentukan batas sesi per ruang berdasarkan jadwal khusus
                        ruang_sekolah_ini['Batas Sesi'] = 5
                        ruang_sekolah_ini['is_khusus'] = False
                        if not df_jadwal_khusus.empty and 'ruang' in df_jadwal_khusus.columns:
                            cek_khusus = df_jadwal_khusus[
                                (df_jadwal_khusus['id_sekolah'] == str(kode_sekolah_terpilih)) & 
                                (df_jadwal_khusus['tanggal'] == str(pilih_tanggal))
                            ]
                            if not cek_khusus.empty:
                                ruang_khusus_list = cek_khusus['ruang'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper().tolist()
                                ruang_sekolah_ini.loc[ruang_sekolah_ini['Ruang_std'].isin(ruang_khusus_list), 'Batas Sesi'] = 2
                                ruang_sekolah_ini.loc[ruang_sekolah_ini['Ruang_std'].isin(ruang_khusus_list), 'is_khusus'] = True
                        
                        # Hitung jumlah kolom yang ditampilkan
                        if not df_detail.empty:
                            ruang_terpakai = df_detail['ruang_std'].unique()
                            batas_sesi_terpakai = ruang_sekolah_ini[ruang_sekolah_ini['Ruang_std'].isin(ruang_terpakai)]['Batas Sesi']
                            max_sesi = int(batas_sesi_terpakai.max()) if not batas_sesi_terpakai.empty else 5
                        else:
                            max_sesi = 2 if ruang_sekolah_ini['is_khusus'].any() else 5
                        
                        # Ringkasan Harian
                        with st.expander("👀 Klik di sini untuk melihat Ringkasan Harian (Kapasitas Total)"):
                            if not df_detail.empty:
                                kursi_terpakai_harian = df_detail.groupby('ruang_std').size().reset_index(name='Kursi Terpakai')
                            else:
                                kursi_terpakai_harian = pd.DataFrame(columns=['ruang_std', 'Kursi Terpakai'])
                            
                            ruang_sekolah_ini['Total Kapasitas Harian'] = ruang_sekolah_ini['kapasitas'] * ruang_sekolah_ini['Batas Sesi']
                            rekap_ruang = pd.merge(ruang_sekolah_ini[['Ruang', 'nama_ruang', 'Total Kapasitas Harian', 'Ruang_std']], 
                                                   kursi_terpakai_harian, left_on='Ruang_std', right_on='ruang_std', how='left')
                            rekap_ruang['Kursi Terpakai'] = rekap_ruang['Kursi Terpakai'].fillna(0).astype(int)
                            rekap_ruang['Sisa Kursi'] = rekap_ruang['Total Kapasitas Harian'] - rekap_ruang['Kursi Terpakai']
                            rekap_ruang['Kuota Terisi / Kapasitas Harian'] = rekap_ruang['Kursi Terpakai'].astype(str) + " / " + rekap_ruang['Total Kapasitas Harian'].astype(int).astype(str)
                            rekap_ruang['Status Harian'] = rekap_ruang.apply(
                                lambda x: "🔴 Penuh" if x['Sisa Kursi'] <= 0 else ("🟡 Cukup" if x['Kursi Terpakai'] > 0 else "🟢 Kosong"), axis=1
                            )
                            tabel_harian = rekap_ruang[['Ruang', 'nama_ruang', 'Kuota Terisi / Kapasitas Harian', 'Sisa Kursi', 'Status Harian']].copy()
                            tabel_harian.rename(columns={'Ruang': 'Nomor Ruang', 'nama_ruang': 'Nama Lokasi'}, inplace=True)
                            st.dataframe(tabel_harian, use_container_width=True, hide_index=True)
                            
                            col_a, col_b, col_c = st.columns(3)
                            total_kapasitas_harian = ruang_sekolah_ini['Total Kapasitas Harian'].sum()
                            col_a.metric("Total Kapasitas Harian", int(total_kapasitas_harian))
                            col_b.metric("Total Kursi Terpakai Harian", rekap_ruang['Kursi Terpakai'].sum())
                            col_c.metric("Total Sisa Kursi Harian", rekap_ruang['Sisa Kursi'].sum())
                        
                        st.divider()
                        
                        # Rincian per sesi
                        st.subheader("🕒 Rincian Keterisian per Sesi")
                        st.markdown("*(Warna sel: 🟩 Kosong | 🟨 Terisi Sebagian | 🟥 Penuh | ⬜ Strip (-) = Ruang tidak buka sesi tsb)*")
                        
                        if not df_detail.empty:
                            pivot_sesi = pd.crosstab(df_detail['ruang_std'], df_detail['kode_sesi_str'])
                        else:
                            pivot_sesi = pd.DataFrame(index=ruang_sekolah_ini['Ruang_std'])
                        
                        df_matrix_sesi = ruang_sekolah_ini[['Ruang', 'nama_ruang', 'kapasitas', 'is_khusus', 'Batas Sesi', 'Ruang_std']].copy()
                        df_matrix_sesi = pd.merge(df_matrix_sesi, pivot_sesi, left_on='Ruang_std', right_index=True, how='left')
                        
                        for sesi in range(1, max_sesi + 1):
                            sesi_str = str(sesi)
                            if sesi_str not in df_matrix_sesi.columns:
                                df_matrix_sesi[sesi_str] = 0
                            df_matrix_sesi[sesi_str] = df_matrix_sesi[sesi_str].fillna(0).astype(int)
                            df_matrix_sesi[f'Sesi {sesi}'] = df_matrix_sesi.apply(
                                lambda row, s=sesi, c=sesi_str: "-" if s > row['Batas Sesi'] else f"{int(row[c])} / {row['kapasitas']}", axis=1
                            )
                        
                        kolom_sesi_dinamis = [f'Sesi {i}' for i in range(1, max_sesi + 1)]
                        kolom_tampil_sesi = ['Ruang', 'nama_ruang'] + kolom_sesi_dinamis
                        df_tampil_sesi = df_matrix_sesi[kolom_tampil_sesi].rename(columns={'Ruang': 'Nomor Ruang', 'nama_ruang': 'Nama Lokasi'})
                        
                        def style_matrix_sesi(row):
                            styles = []
                            for col in row.index:
                                if str(col).startswith('Sesi'):
                                    val = str(row[col])
                                    if val == "-":
                                        styles.append('background-color: #f0f2f6; color: #a3a8b8; text-align: center;')
                                    else:
                                        try:
                                            terisi_str, kap_str = val.split(' / ')
                                            terisi, kap = int(terisi_str), int(kap_str)
                                            if terisi >= kap:
                                                styles.append('background-color: #ffcccc; color: #990000; font-weight: bold;')
                                            elif terisi == 0:
                                                styles.append('background-color: #ccffcc; color: #006600;')
                                            else:
                                                styles.append('background-color: #fff9cc; color: #997a00;')
                                        except:
                                            styles.append('')
                                else:
                                    styles.append('')
                            return styles
                        
                        st.dataframe(df_tampil_sesi.style.apply(style_matrix_sesi, axis=1), use_container_width=True, hide_index=True)
                    elif not ruang_sekolah_ini.empty and not pilih_tanggal:
                        st.info("Pilih tanggal untuk melihat detail.")
                    else:
                        st.warning(f"Data kapasitas ruang untuk kode sekolah '{kode_sekolah_terpilih}' tidak ditemukan di file Master Ruang.")