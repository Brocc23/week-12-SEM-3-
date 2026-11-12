"""Model Barang Jaminan dan hierarki taksiran agunan."""
import json
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


class BarangJaminan(ABC):
    """Kelas abstrak untuk barang jaminan agunan gadai."""

    def __init__(
        self,
        id: int | None,
        kode: str,
        nasabah_id: int,
        jenis: str,
        deskripsi: str,
        atribut: dict,
        nilai_taksiran: Decimal | str | int = 0,
        status: str = "TERGADAI",
        penaksir_id: int | None = None,
    ):
        self.id = id
        self.kode = kode
        self.nasabah_id = nasabah_id
        self.jenis = jenis
        self.deskripsi = deskripsi
        self.atribut = atribut if isinstance(atribut, dict) else json.loads(atribut or "{}")
        self.penaksir_id = penaksir_id

        # Enkapsulasi atribut sensitif
        self.__nilai_taksiran = Decimal(str(nilai_taksiran or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__status = status

    @property
    def nilai_taksiran(self) -> Decimal:
        return self.__nilai_taksiran

    @nilai_taksiran.setter
    def nilai_taksiran(self, nilai: Decimal | str | int):
        dec = Decimal(str(nilai or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if dec < 0:
            raise ValueError("Nilai taksiran tidak boleh bernilai negatif")
        self.__nilai_taksiran = dec

    @property
    def status(self) -> str:
        return self.__status

    @status.setter
    def status(self, status_baru: str):
        status_valid = {
            "TERGADAI",
            "JATUH_TEMPO",
            "DALAM_PROSES_LELANG",
            "TERLELANG",
            "LUNAS",
            "DIKEMBALIKAN",
        }
        if status_baru not in status_valid:
            raise ValueError(f"Status barang tidak valid: {status_baru}")
        self.__status = status_baru

    @abstractmethod
    def hitung_taksiran(self, parameter: dict) -> Decimal:
        """Menghitung nilai taksiran agunan berbasis parameter pasar."""
        pass

    @abstractmethod
    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        """Persentase batas pinjaman maksimal (LTV) terhadap nilai taksiran."""
        pass

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kode": self.kode,
            "nasabah_id": self.nasabah_id,
            "jenis": self.jenis,
            "deskripsi": self.deskripsi,
            "atribut": json.dumps(self.atribut),
            "nilai_taksiran": self.__nilai_taksiran,
            "status": self.__status,
            "penaksir_id": self.penaksir_id,
        }


def _get_faktor_kondisi(kondisi: str, parameter: dict) -> Decimal:
    kondisi_clean = (kondisi or "BAIK").upper()
    if kondisi_clean == "BAIK":
        return Decimal(str(parameter.get("faktor_kondisi_baik", "1.00")))
    elif kondisi_clean == "CUKUP":
        return Decimal(str(parameter.get("faktor_kondisi_cukup", "0.80")))
    elif kondisi_clean == "BURUK":
        return Decimal(str(parameter.get("faktor_kondisi_buruk", "0.60")))
    return Decimal("1.00")


class Emas(BarangJaminan):
    """Barang jaminan jenis emas (perhiasan/logam mulia)."""

    def __init__(self, id, kode, nasabah_id, deskripsi, atribut, nilai_taksiran=0, status="TERGADAI", penaksir_id=None):
        super().__init__(id, kode, nasabah_id, "EMAS", deskripsi, atribut, nilai_taksiran, status, penaksir_id)

    def hitung_taksiran(self, parameter: dict) -> Decimal:
        # Rumus: T = berat * (kadar / 24) * harga_emas_per_gram
        berat = Decimal(str(self.atribut.get("berat", 0)))
        kadar = Decimal(str(self.atribut.get("kadar", 0)))
        harga = Decimal(str(parameter.get("harga_emas_per_gram", "1000000")))
        if berat <= 0 or kadar <= 0:
            return Decimal("0")
        taksiran = (berat * (kadar / Decimal("24")) * harga)
        self.nilai_taksiran = taksiran
        return self.nilai_taksiran

    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        return Decimal(str(parameter.get("persen_pinjaman_emas", "0.90")))


class Kendaraan(BarangJaminan):
    """Barang jaminan jenis kendaraan bermotor."""

    def __init__(self, id, kode, nasabah_id, deskripsi, atribut, nilai_taksiran=0, status="TERGADAI", penaksir_id=None):
        super().__init__(id, kode, nasabah_id, "KENDARAAN", deskripsi, atribut, nilai_taksiran, status, penaksir_id)

    def hitung_taksiran(self, parameter: dict) -> Decimal:
        # Rumus: T = Hp * Fu * Fk
        hp = Decimal(str(self.atribut.get("harga_pasar", 0)))
        current_year = date.today().year
        tahun = self.atribut.get("tahun")
        if tahun is not None:
            umur = max(0, current_year - int(tahun))
        else:
            umur = int(self.atribut.get("umur", 0))

        fu = max(Decimal("0.3"), Decimal("1.0") - Decimal("0.07") * Decimal(umur))
        fk = _get_faktor_kondisi(self.atribut.get("kondisi", "BAIK"), parameter)
        taksiran = hp * fu * fk
        self.nilai_taksiran = taksiran
        return self.nilai_taksiran

    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        return Decimal(str(parameter.get("persen_pinjaman_kendaraan", "0.75")))


class Elektronik(BarangJaminan):
    """Barang jaminan alat elektronik umum."""

    def __init__(self, id, kode, nasabah_id, deskripsi, atribut, nilai_taksiran=0, status="TERGADAI", penaksir_id=None):
        super().__init__(id, kode, nasabah_id, "ELEKTRONIK", deskripsi, atribut, nilai_taksiran, status, penaksir_id)

    def hitung_taksiran(self, parameter: dict) -> Decimal:
        # Rumus: T = Hp * ((1 - d) ** n) * Fk
        hp = Decimal(str(self.atribut.get("harga_pasar", 0)))
        umur = int(self.atribut.get("umur", 0))
        d = Decimal(str(parameter.get("penyusutan_elektronik", "0.15")))
        faktor_penyusutan = (Decimal("1") - d) ** umur
        fk = _get_faktor_kondisi(self.atribut.get("kondisi", "BAIK"), parameter)
        taksiran = hp * faktor_penyusutan * fk
        self.nilai_taksiran = taksiran
        return self.nilai_taksiran

    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        return Decimal(str(parameter.get("persen_pinjaman_elektronik", "0.60")))


class Laptop(BarangJaminan):
    """Barang jaminan jenis laptop / notebook."""

    def __init__(self, id, kode, nasabah_id, deskripsi, atribut, nilai_taksiran=0, status="TERGADAI", penaksir_id=None):
        super().__init__(id, kode, nasabah_id, "LAPTOP", deskripsi, atribut, nilai_taksiran, status, penaksir_id)

    def hitung_taksiran(self, parameter: dict) -> Decimal:
        # Rumus: T = Hp * Fs * Fu * Fk
        hp = Decimal(str(self.atribut.get("harga_pasar", 0)))
        spec = (self.atribut.get("spesifikasi") or "MID").upper()
        if spec == "LOW":
            fs = Decimal(str(parameter.get("faktor_spesifikasi_low", "0.70")))
        elif spec == "HIGH":
            fs = Decimal(str(parameter.get("faktor_spesifikasi_high", "1.20")))
        else:
            fs = Decimal(str(parameter.get("faktor_spesifikasi_mid", "1.00")))

        umur = int(self.atribut.get("umur", 0))
        fu = max(Decimal("0.2"), Decimal("1.0") - Decimal("0.12") * Decimal(umur))
        fk = _get_faktor_kondisi(self.atribut.get("kondisi", "BAIK"), parameter)
        taksiran = hp * fs * fu * fk
        self.nilai_taksiran = taksiran
        return self.nilai_taksiran

    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        return Decimal(str(parameter.get("persen_pinjaman_laptop", "0.60")))


class Lainnya(BarangJaminan):
    """Barang jaminan jenis lainnya (berharga umum)."""

    def __init__(self, id, kode, nasabah_id, deskripsi, atribut, nilai_taksiran=0, status="TERGADAI", penaksir_id=None):
        super().__init__(id, kode, nasabah_id, "LAINNYA", deskripsi, atribut, nilai_taksiran, status, penaksir_id)

    def hitung_taksiran(self, parameter: dict) -> Decimal:
        # Rumus: T = Hp * Fk
        hp = Decimal(str(self.atribut.get("harga_pasar", 0)))
        fk = _get_faktor_kondisi(self.atribut.get("kondisi", "BAIK"), parameter)
        taksiran = hp * fk
        self.nilai_taksiran = taksiran
        return self.nilai_taksiran

    def persen_pinjaman_default(self, parameter: dict) -> Decimal:
        return Decimal(str(parameter.get("persen_pinjaman_lainnya", "0.50")))


def buat_barang(data: dict) -> BarangJaminan:
    """Factory helper untuk membuat instance turunan BarangJaminan."""
    jenis = (data.get("jenis") or "").upper()
    kwargs = {
        "id": data.get("id"),
        "kode": data.get("kode", ""),
        "nasabah_id": data.get("nasabah_id"),
        "deskripsi": data.get("deskripsi", ""),
        "atribut": data.get("atribut", {}),
        "nilai_taksiran": data.get("nilai_taksiran", 0),
        "status": data.get("status", "TERGADAI"),
        "penaksir_id": data.get("penaksir_id"),
    }
    if jenis == "EMAS":
        return Emas(**kwargs)
    elif jenis == "KENDARAAN":
        return Kendaraan(**kwargs)
    elif jenis == "ELEKTRONIK":
        return Elektronik(**kwargs)
    elif jenis == "LAPTOP":
        return Laptop(**kwargs)
    elif jenis == "LAINNYA":
        return Lainnya(**kwargs)
    raise ValueError(f"Jenis barang jaminan tidak valid: {jenis}")
