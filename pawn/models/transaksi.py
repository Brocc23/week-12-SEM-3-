"""Model Transaksi keuangan dengan abstraksi dan polimorfisme."""
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from pawn.models.pinjaman import Pinjaman


class Transaksi(ABC):
    """Kelas abstrak untuk semua transaksi kasir dan mutasi pinjaman."""

    def __init__(
        self,
        id: int | None,
        no_transaksi: str,
        pinjaman_id: int,
        jenis: str,
        jumlah: Decimal | str | int,
        metode: str | None,
        status: str,
        waktu: str,
        petugas_id: int,
        keterangan: str = "",
    ):
        self.id = id
        self.no_transaksi = no_transaksi
        self.pinjaman_id = pinjaman_id
        self.jenis = jenis
        self.waktu = waktu
        self.petugas_id = petugas_id
        self.keterangan = keterangan

        # Enkapsulasi data keuangan sensitif
        self.__jumlah = Decimal(str(jumlah)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__metode = (metode or "TUNAI").upper()
        self.__status = status

    @property
    def jumlah(self) -> Decimal:
        return self.__jumlah

    @property
    def metode(self) -> str:
        return self.__metode

    @property
    def status(self) -> str:
        return self.__status

    @status.setter
    def status(self, val: str):
        if val not in ("BERHASIL", "GAGAL"):
            raise ValueError(f"Status transaksi tidak valid: {val}")
        self.__status = val

    @abstractmethod
    def eksekusi(self, pinjaman: Pinjaman) -> dict:
        """Mengeksekusi mutasi saldo pada entitas Pinjaman secara polimorfis."""
        pass

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "no_transaksi": self.no_transaksi,
            "pinjaman_id": self.pinjaman_id,
            "jenis": self.jenis,
            "jumlah": self.__jumlah,
            "metode": self.__metode,
            "status": self.__status,
            "waktu": self.waktu,
            "petugas_id": self.petugas_id,
            "keterangan": self.keterangan,
        }


class TransaksiGadai(Transaksi):
    """Transaksi pencairan dana awal pinjaman gadai kepada nasabah."""

    def __init__(self, id, no_transaksi, pinjaman_id, jumlah, metode, status, waktu, petugas_id, keterangan=""):
        super().__init__(id, no_transaksi, pinjaman_id, "GADAI", jumlah, metode, status, waktu, petugas_id, keterangan)

    def eksekusi(self, pinjaman: Pinjaman) -> dict:
        self.status = "BERHASIL"
        return {
            "jenis": "GADAI",
            "pencairan": self.jumlah,
            "pokok": pinjaman.pokok,
            "sisa_pokok": pinjaman.sisa_pokok,
            "status_pinjaman": pinjaman.status,
        }


class TransaksiAngsuran(Transaksi):
    """Transaksi pembayaran cicilan/angsuran pinjaman berjalan."""

    def __init__(self, id, no_transaksi, pinjaman_id, jumlah, metode, status, waktu, petugas_id, keterangan=""):
        super().__init__(id, no_transaksi, pinjaman_id, "ANGSURAN", jumlah, metode, status, waktu, petugas_id, keterangan)

    def eksekusi(self, pinjaman: Pinjaman) -> dict:
        hasil = pinjaman.terapkan_pembayaran(self.jumlah)
        self.status = "BERHASIL"
        return hasil


class TransaksiPelunasan(Transaksi):
    """Transaksi pembayaran pelunasan seluruh kewajiban pinjaman."""

    def __init__(self, id, no_transaksi, pinjaman_id, jumlah, metode, status, waktu, petugas_id, keterangan=""):
        super().__init__(id, no_transaksi, pinjaman_id, "PELUNASAN", jumlah, metode, status, waktu, petugas_id, keterangan)

    def eksekusi(self, pinjaman: Pinjaman) -> dict:
        total_kewajiban = pinjaman.hitung_total_kewajiban()
        if self.jumlah < total_kewajiban:
            self.status = "GAGAL"
            raise ValueError(f"Jumlah pembayaran Rp {self.jumlah} kurang dari total kewajiban Rp {total_kewajiban}")

        hasil = pinjaman.terapkan_pembayaran(self.jumlah)
        pinjaman.status = "LUNAS"
        self.status = "BERHASIL"
        hasil["status"] = "LUNAS"
        return hasil


class TransaksiPerpanjangan(Transaksi):
    """Transaksi pembayaran biaya administrasi perpanjangan tenor."""

    def __init__(self, id, no_transaksi, pinjaman_id, jumlah, metode, status, waktu, petugas_id, keterangan=""):
        super().__init__(id, no_transaksi, pinjaman_id, "PERPANJANGAN", jumlah, metode, status, waktu, petugas_id, keterangan)

    def eksekusi(self, pinjaman: Pinjaman) -> dict:
        self.status = "BERHASIL"
        return {
            "biaya_perpanjangan": self.jumlah,
            "tgl_jatuh_tempo_baru": str(pinjaman.tgl_jatuh_tempo),
            "jumlah_perpanjangan": pinjaman.jumlah_perpanjangan,
        }


def buat_transaksi(data: dict) -> Transaksi:
    """Factory helper untuk membuat instance turunan Transaksi."""
    jenis = (data.get("jenis") or "").upper()
    kwargs = {
        "id": data.get("id"),
        "no_transaksi": data.get("no_transaksi", ""),
        "pinjaman_id": data.get("pinjaman_id"),
        "jumlah": data.get("jumlah", 0),
        "metode": data.get("metode", "TUNAI"),
        "status": data.get("status", "BERHASIL"),
        "waktu": data.get("waktu", ""),
        "petugas_id": data.get("petugas_id"),
        "keterangan": data.get("keterangan", ""),
    }
    if jenis == "GADAI":
        return TransaksiGadai(**kwargs)
    elif jenis == "ANGSURAN":
        return TransaksiAngsuran(**kwargs)
    elif jenis == "PELUNASAN":
        return TransaksiPelunasan(**kwargs)
    elif jenis == "PERPANJANGAN":
        return TransaksiPerpanjangan(**kwargs)
    raise ValueError(f"Jenis transaksi tidak valid: {jenis}")
