"""Layanan Penaksiran Nilai Agunan dan Perhitungan Maksimal Pinjaman."""
from decimal import Decimal, ROUND_HALF_UP
from pawn.errors import ValidasiError
from pawn.models.barang import buat_barang
from pawn.repository.repos import ParameterRepo


class PenaksiranService:
    """Melakukan penilaian agunan secara matematis berbasis parameter pasar terkini."""

    def __init__(self, parameter_repo: ParameterRepo):
        self.parameter_repo = parameter_repo

    def ambil_semua_parameter(self) -> dict:
        """Memuat seluruh parameter perhitungan dari repositori ke dalam memori."""
        semua = self.parameter_repo.all()
        kamus = {r["kunci"]: r["nilai"] for r in semua}

        # Nilai default sesuai spesifikasi sistem
        default = {
            "harga_emas_per_gram": "1000000",
            "persen_pinjaman_emas": "0.90",
            "persen_pinjaman_kendaraan": "0.75",
            "persen_pinjaman_elektronik": "0.60",
            "persen_pinjaman_laptop": "0.60",
            "persen_pinjaman_lainnya": "0.50",
            "faktor_kondisi_baik": "1.00",
            "faktor_kondisi_cukup": "0.80",
            "faktor_kondisi_buruk": "0.60",
            "faktor_spesifikasi_low": "0.70",
            "faktor_spesifikasi_mid": "1.00",
            "faktor_spesifikasi_high": "1.20",
            "penyusutan_elektronik": "0.15",
            "bunga_per_periode": "0.012",
            "biaya_admin_persen": "0.01",
            "denda_per_hari": "0.002",
            "biaya_perpanjangan_persen": "0.01",
            "maks_perpanjangan": "2",
            "tenor_hari_default": "120",
            "masa_tenggang_hari": "14",
        }
        for k, v in default.items():
            if k not in kamus:
                kamus[k] = v
        return kamus

    def hitung_taksiran(self, jenis: str, atribut: dict) -> dict:
        """
        Menghitung taksiran nilai agunan dan batas pinjaman (LTV).
        Mengembalikan: dict(nilai_taksiran, persen, maks_pinjaman) dalam bentuk Decimal.
        """
        jenis_clean = (jenis or "").upper().strip()
        if jenis_clean not in ("EMAS", "KENDARAAN", "ELEKTRONIK", "LAPTOP", "LAINNYA"):
            raise ValidasiError(f"Jenis barang '{jenis}' tidak valid. Pilihan: EMAS, KENDARAAN, ELEKTRONIK, LAPTOP, LAINNYA")

        if not isinstance(atribut, dict):
            raise ValidasiError("Atribut taksiran harus berupa dictionary data")

        # Validasi spesifik per jenis barang
        if jenis_clean == "EMAS":
            berat = Decimal(str(atribut.get("berat", 0)))
            kadar = Decimal(str(atribut.get("kadar", 0)))
            if berat <= Decimal("0"):
                raise ValidasiError("Berat emas harus lebih dari 0 gram")
            if kadar <= Decimal("0") or kadar > Decimal("24"):
                raise ValidasiError("Kadar emas harus antara 1 sampai 24 karat")

        elif jenis_clean == "KENDARAAN":
            hp = Decimal(str(atribut.get("harga_pasar", 0)))
            if hp <= Decimal("0"):
                raise ValidasiError("Harga pasar kendaraan harus lebih dari 0")

        elif jenis_clean == "ELEKTRONIK":
            hp = Decimal(str(atribut.get("harga_pasar", 0)))
            if hp <= Decimal("0"):
                raise ValidasiError("Harga pasar elektronik harus lebih dari 0")

        elif jenis_clean == "LAPTOP":
            hp = Decimal(str(atribut.get("harga_pasar", 0)))
            if hp <= Decimal("0"):
                raise ValidasiError("Harga pasar laptop harus lebih dari 0")

        elif jenis_clean == "LAINNYA":
            hp = Decimal(str(atribut.get("harga_pasar", 0)))
            if hp <= Decimal("0"):
                raise ValidasiError("Harga pasar barang lainnya harus lebih dari 0")

        params = self.ambil_semua_parameter()

        dummy_data = {
            "id": None,
            "kode": "SIMULASI",
            "nasabah_id": 0,
            "jenis": jenis_clean,
            "deskripsi": "Simulasi Taksiran",
            "atribut": atribut,
            "nilai_taksiran": 0,
            "status": "TERGADAI",
            "penaksir_id": None,
        }

        barang = buat_barang(dummy_data)
        nilai_taksiran = barang.hitung_taksiran(params).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        persen = barang.persen_pinjaman_default(params)
        maks_pinjaman = (nilai_taksiran * persen).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return {
            "nilai_taksiran": nilai_taksiran,
            "persen": persen,
            "maks_pinjaman": maks_pinjaman,
        }
