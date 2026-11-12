"""Initial database seeder with branches, default users, parameters, and sample customers."""

from pawn.repository.database import Database, hash_password
from pawn.repository.repos import (
    CabangRepo,
    NasabahRepo,
    ParameterRepo,
    PenggunaRepo,
)

DEFAULT_PARAMETERS = {
    # Taksiran & Rasio Maksimum Pinjaman
    "harga_emas_per_gram": "1000000",
    "persen_pinjaman_emas": "0.90",
    "persen_pinjaman_kendaraan": "0.75",
    "persen_pinjaman_elektronik": "0.60",
    "persen_pinjaman_laptop": "0.60",
    "persen_pinjaman_lainnya": "0.50",
    # Faktor Kondisi
    "faktor_kondisi_BAIK": "1.00",
    "faktor_kondisi_CUKUP": "0.80",
    "faktor_kondisi_BURUK": "0.60",
    "faktor_kondisi_baik": "1.00",
    "faktor_kondisi_cukup": "0.80",
    "faktor_kondisi_buruk": "0.60",
    # Faktor Kendaraan
    "faktor_usia_kendaraan_drop": "0.07",
    "faktor_usia_kendaraan_min": "0.30",
    # Faktor Laptop
    "faktor_spesifikasi_LOW": "0.70",
    "faktor_spesifikasi_MID": "1.00",
    "faktor_spesifikasi_HIGH": "1.20",
    "faktor_spesifikasi_low": "0.70",
    "faktor_spesifikasi_mid": "1.00",
    "faktor_spesifikasi_high": "1.20",
    "faktor_usia_laptop_drop": "0.12",
    "faktor_usia_laptop_min": "0.20",
    # Depresiasi Elektronik
    "penyusutan_elektronik": "0.15",
    # Bunga & Tarif Pinjaman
    "bunga_per_periode": "0.012",
    "hari_per_periode": "15",
    "biaya_admin_persen": "0.01",
    "denda_per_hari": "0.002",
    "biaya_perpanjangan_persen": "0.01",
    "maks_perpanjangan": "2",
    "tenor_hari_default": "120",
    "masa_tenggang_hari": "14",
    "maks_tahap_notifikasi": "2",
    "seq_nasabah": "3",
}


def seed_if_empty(db: Database) -> bool:
    """Seed initial branches, users, parameters, and customers if database is empty."""
    db.init_schema()
    cabang_repo = CabangRepo(db)
    param_repo = ParameterRepo(db)
    if cabang_repo.all():
        # Ensure missing default parameters are inserted into existing databases
        for k, v in DEFAULT_PARAMETERS.items():
            if param_repo.get(k) is None:
                param_repo.set_value(k, v)
        return False

    pengguna_repo = PenggunaRepo(db)
    param_repo = ParameterRepo(db)
    nasabah_repo = NasabahRepo(db)

    with db.transaction():
        # 1. Seed Parameters
        for k, v in DEFAULT_PARAMETERS.items():
            param_repo.set_value(k, v)

        # 2. Seed Branches (JKT & BDG)
        id_jkt = cabang_repo.insert({
            "kode": "JKT",
            "nama": "Cabang Jakarta Pusat",
            "alamat": "Jl. MH Thamrin No. 10, Jakarta Pusat",
        })
        id_bdg = cabang_repo.insert({
            "kode": "BDG",
            "nama": "Cabang Bandung Merdeka",
            "alamat": "Jl. Merdeka No. 45, Bandung",
        })

        # 3. Seed Users
        users = [
            ("admin", "admin123", "ADMIN", "Administrator Pusat", None),
            ("petugas1", "petugas123", "PETUGAS", "Budi Santoso", id_jkt),
            ("penaksir1", "penaksir123", "PENAKSIR", "Siti Aminah", id_jkt),
            ("petugas2", "petugas123", "PETUGAS", "Asep Sunandar", id_bdg),
            ("penaksir2", "penaksir123", "PENAKSIR", "Rina Marlina", id_bdg),
        ]
        for uname, pwd, role, nama, cid in users:
            pw_hash, salt = hash_password(pwd)
            pengguna_repo.insert({
                "cabang_id": cid,
                "username": uname,
                "password_hash": pw_hash,
                "salt": salt,
                "role": role,
                "nama": nama,
                "aktif": 1,
            })

        # 4. Seed Sample Customers
        customers = [
            (id_jkt, "NSB-0001", "3171012345670001", "Ahmad Dahlan", "Jl. Salemba Raya No. 12, Jakarta", "081234567890", "ahmad.dahlan@example.com", "2026-01-15"),
            (id_jkt, "NSB-0002", "3171012345670002", "Dewi Lestari", "Jl. Senopati No. 8, Jakarta", "081234567891", "dewi.lestari@example.com", "2026-02-01"),
            (id_bdg, "NSB-0003", "3273012345670001", "Rian Hidayat", "Jl. Dago No. 88, Bandung", "081234567892", "rian.hidayat@example.com", "2026-02-10"),
        ]
        for cid, kode, nik, nama, alamat, telp, email, tgl in customers:
            nasabah_repo.insert({
                "cabang_id": cid,
                "kode": kode,
                "nik": nik,
                "nama": nama,
                "alamat": alamat,
                "telepon": telp,
                "email": email,
                "tgl_daftar": tgl,
                "status": "AKTIF",
            })

    return True
