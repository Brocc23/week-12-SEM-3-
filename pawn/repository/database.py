"""Database connection, schema definitions, transactions, and password utilities."""

import hashlib
import hmac
import os
import secrets
import shutil
import sqlite3
from contextlib import contextmanager

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cabang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode TEXT UNIQUE NOT NULL,
    nama TEXT NOT NULL,
    alamat TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pengguna (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabang_id INTEGER,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'PETUGAS', 'PENAKSIR')),
    nama TEXT NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (cabang_id) REFERENCES cabang(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS nasabah (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabang_id INTEGER NOT NULL,
    kode TEXT UNIQUE NOT NULL,
    nik TEXT UNIQUE NOT NULL,
    nama TEXT NOT NULL,
    alamat TEXT NOT NULL,
    telepon TEXT NOT NULL,
    email TEXT NOT NULL,
    tgl_daftar TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AKTIF' CHECK(status IN ('AKTIF', 'DITANGGUHKAN')),
    FOREIGN KEY (cabang_id) REFERENCES cabang(id)
);

CREATE TABLE IF NOT EXISTS barang_jaminan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode TEXT UNIQUE NOT NULL,
    nasabah_id INTEGER NOT NULL,
    jenis TEXT NOT NULL CHECK(jenis IN ('EMAS', 'KENDARAAN', 'ELEKTRONIK', 'LAPTOP', 'LAINNYA')),
    deskripsi TEXT NOT NULL,
    atribut TEXT NOT NULL,
    nilai_taksiran TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('TERGADAI', 'JATUH_TEMPO', 'DALAM_PROSES_LELANG', 'TERLELANG', 'LUNAS', 'DIKEMBALIKAN')),
    penaksir_id INTEGER NOT NULL,
    FOREIGN KEY (nasabah_id) REFERENCES nasabah(id),
    FOREIGN KEY (penaksir_id) REFERENCES pengguna(id)
);

CREATE TABLE IF NOT EXISTS pinjaman (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_kontrak TEXT UNIQUE NOT NULL,
    cabang_id INTEGER NOT NULL,
    nasabah_id INTEGER NOT NULL,
    barang_id INTEGER NOT NULL,
    petugas_id INTEGER NOT NULL,
    penaksir_id INTEGER NOT NULL,
    nilai_taksiran TEXT NOT NULL,
    persen_pinjaman TEXT NOT NULL,
    pokok TEXT NOT NULL,
    sisa_pokok TEXT NOT NULL,
    bunga_terutang TEXT NOT NULL,
    biaya_admin_terutang TEXT NOT NULL,
    denda_terutang TEXT NOT NULL,
    suku_bunga_periode TEXT NOT NULL,
    tgl_transaksi TEXT NOT NULL,
    tgl_jatuh_tempo TEXT NOT NULL,
    jumlah_perpanjangan INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK(status IN ('AKTIF', 'JATUH_TEMPO', 'DALAM_PROSES_LELANG', 'LUNAS', 'TERLELANG', 'DIKEMBALIKAN')),
    FOREIGN KEY (cabang_id) REFERENCES cabang(id),
    FOREIGN KEY (nasabah_id) REFERENCES nasabah(id),
    FOREIGN KEY (barang_id) REFERENCES barang_jaminan(id),
    FOREIGN KEY (petugas_id) REFERENCES pengguna(id),
    FOREIGN KEY (penaksir_id) REFERENCES pengguna(id)
);

CREATE TABLE IF NOT EXISTS transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_transaksi TEXT UNIQUE NOT NULL,
    pinjaman_id INTEGER NOT NULL,
    jenis TEXT NOT NULL CHECK(jenis IN ('GADAI', 'ANGSURAN', 'PELUNASAN', 'PERPANJANGAN')),
    jumlah TEXT NOT NULL,
    metode TEXT CHECK(metode IS NULL OR metode IN ('TUNAI', 'TRANSFER', 'QRIS', 'EWALLET')),
    status TEXT NOT NULL CHECK(status IN ('BERHASIL', 'GAGAL')),
    waktu TEXT NOT NULL,
    petugas_id INTEGER NOT NULL,
    keterangan TEXT,
    FOREIGN KEY (pinjaman_id) REFERENCES pinjaman(id),
    FOREIGN KEY (petugas_id) REFERENCES pengguna(id)
);

CREATE TABLE IF NOT EXISTS perpanjangan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pinjaman_id INTEGER NOT NULL,
    tgl_lama TEXT NOT NULL,
    tgl_baru TEXT NOT NULL,
    biaya TEXT NOT NULL,
    waktu TEXT NOT NULL,
    petugas_id INTEGER NOT NULL,
    FOREIGN KEY (pinjaman_id) REFERENCES pinjaman(id),
    FOREIGN KEY (petugas_id) REFERENCES pengguna(id)
);

CREATE TABLE IF NOT EXISTS gudang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_barang TEXT UNIQUE NOT NULL,
    barang_id INTEGER NOT NULL,
    pinjaman_id INTEGER NOT NULL,
    lokasi TEXT NOT NULL,
    tgl_masuk TEXT NOT NULL,
    kondisi TEXT NOT NULL,
    petugas_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (barang_id) REFERENCES barang_jaminan(id),
    FOREIGN KEY (pinjaman_id) REFERENCES pinjaman(id),
    FOREIGN KEY (petugas_id) REFERENCES pengguna(id)
);

CREATE TABLE IF NOT EXISTS notifikasi_lelang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pinjaman_id INTEGER NOT NULL,
    tahap INTEGER NOT NULL,
    tanggal TEXT NOT NULL,
    pesan TEXT NOT NULL,
    FOREIGN KEY (pinjaman_id) REFERENCES pinjaman(id)
);

CREATE TABLE IF NOT EXISTS lelang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pinjaman_id INTEGER UNIQUE NOT NULL,
    harga_lelang TEXT NOT NULL,
    total_kewajiban TEXT NOT NULL,
    selisih TEXT NOT NULL,
    hasil TEXT NOT NULL CHECK(hasil IN ('SURPLUS', 'IMPAS', 'DEFISIT')),
    hak_nasabah TEXT NOT NULL,
    kerugian TEXT NOT NULL,
    tanggal TEXT NOT NULL,
    FOREIGN KEY (pinjaman_id) REFERENCES pinjaman(id)
);

CREATE TABLE IF NOT EXISTS parameter (
    kunci TEXT PRIMARY KEY,
    nilai TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu TEXT NOT NULL,
    pengguna_id INTEGER,
    aksi TEXT NOT NULL,
    detail TEXT,
    FOREIGN KEY (pengguna_id) REFERENCES pengguna(id)
);

CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is immutable');
END;

CREATE TABLE IF NOT EXISTS jurnal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu TEXT NOT NULL,
    no_ref TEXT NOT NULL,
    akun TEXT NOT NULL,
    debit TEXT NOT NULL DEFAULT '0',
    kredit TEXT NOT NULL DEFAULT '0',
    keterangan TEXT
);

CREATE INDEX IF NOT EXISTS idx_pengguna_cabang ON pengguna(cabang_id);
CREATE INDEX IF NOT EXISTS idx_nasabah_cabang ON nasabah(cabang_id);
CREATE INDEX IF NOT EXISTS idx_barang_nasabah ON barang_jaminan(nasabah_id);
CREATE INDEX IF NOT EXISTS idx_barang_penaksir ON barang_jaminan(penaksir_id);
CREATE INDEX IF NOT EXISTS idx_pinjaman_cabang ON pinjaman(cabang_id);
CREATE INDEX IF NOT EXISTS idx_pinjaman_nasabah ON pinjaman(nasabah_id);
CREATE INDEX IF NOT EXISTS idx_pinjaman_barang ON pinjaman(barang_id);
CREATE INDEX IF NOT EXISTS idx_pinjaman_petugas ON pinjaman(petugas_id);
CREATE INDEX IF NOT EXISTS idx_pinjaman_penaksir ON pinjaman(penaksir_id);
CREATE INDEX IF NOT EXISTS idx_transaksi_pinjaman ON transaksi(pinjaman_id);
CREATE INDEX IF NOT EXISTS idx_transaksi_petugas ON transaksi(petugas_id);
CREATE INDEX IF NOT EXISTS idx_perpanjangan_pinjaman ON perpanjangan(pinjaman_id);
CREATE INDEX IF NOT EXISTS idx_perpanjangan_petugas ON perpanjangan(petugas_id);
CREATE INDEX IF NOT EXISTS idx_gudang_barang ON gudang(barang_id);
CREATE INDEX IF NOT EXISTS idx_gudang_pinjaman ON gudang(pinjaman_id);
CREATE INDEX IF NOT EXISTS idx_gudang_petugas ON gudang(petugas_id);
CREATE INDEX IF NOT EXISTS idx_notifikasi_pinjaman ON notifikasi_lelang(pinjaman_id);
CREATE INDEX IF NOT EXISTS idx_lelang_pinjaman ON lelang(pinjaman_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_pengguna ON audit_log(pengguna_id);
CREATE INDEX IF NOT EXISTS idx_jurnal_ref ON jurnal(no_ref);
"""


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100_000)
    return key.hex(), salt


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Verify password against stored PBKDF2-HMAC-SHA256 hash and salt."""
    computed_hash, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash, hash_hex)


class Database:
    """SQLite database manager with explicit transactions, backups, and WAL support."""

    def __init__(self, path: str = "pegadaian.db"):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        self._tx_depth = 0

    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._conn.isolation_level = None  # Autocommit mode for explicit transaction control
            self._conn.execute("PRAGMA foreign_keys = ON;")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._tx_depth = 0

    @contextmanager
    def transaction(self):
        """Explicit BEGIN / COMMIT, ROLLBACK on exception; nested transactions join outer."""
        conn = self.connection()
        self._tx_depth += 1
        if self._tx_depth == 1:
            conn.execute("BEGIN")
        try:
            yield conn
        except Exception:
            if self._tx_depth > 0:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    # Ignore secondary errors if SQLite auto-rolled-back on trigger ABORT
                    pass
                self._tx_depth = 0
            raise
        else:
            if self._tx_depth == 1:
                conn.execute("COMMIT")
        finally:
            if self._tx_depth > 0:
                self._tx_depth -= 1

    def init_schema(self) -> None:
        """Create tables, indexes, and immutable audit triggers if they do not exist."""
        conn = self.connection()
        conn.executescript(SCHEMA_DDL)

    def backup(self, dest_path: str) -> None:
        """Backup database to dest_path using SQLite backup API."""
        dest_dir = os.path.dirname(os.path.abspath(dest_path))
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        dest_conn = sqlite3.connect(dest_path)
        try:
            with dest_conn:
                self.connection().backup(dest_conn)
        finally:
            dest_conn.close()

    def restore(self, src_path: str) -> None:
        """Validate src_path SQLite schema, copy over, and reopen connection."""
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source backup file not found: {src_path}")

        required_tables = {
            "cabang", "pengguna", "nasabah", "barang_jaminan",
            "pinjaman", "transaksi", "perpanjangan", "gudang",
            "notifikasi_lelang", "lelang", "parameter", "audit_log", "jurnal"
        }
        test_conn = sqlite3.connect(src_path)
        try:
            rows = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            existing_tables = {row[0] for row in rows}
            missing = required_tables - existing_tables
            if missing:
                raise ValueError(f"Invalid backup file; missing tables: {missing}")
        finally:
            test_conn.close()

        if self.path == ":memory:":
            src_conn = sqlite3.connect(src_path)
            try:
                src_conn.backup(self.connection())
            finally:
                src_conn.close()
        else:
            self.close()
            shutil.copyfile(src_path, self.path)
            self.connection()
