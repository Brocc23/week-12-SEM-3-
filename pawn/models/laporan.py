"""Model Pelaporan Keuangan dan Aset Jaminan dengan abstraksi dan polimorfisme."""
from abc import ABC, abstractmethod
from decimal import Decimal


class LaporanKeuangan(ABC):
    """Kelas abstrak dasar untuk generator laporan sistem."""

    @abstractmethod
    def hasilkan(self) -> dict | list[dict]:
        """Menghasilkan struktur data laporan agregat."""
        pass


class LaporanLabaRugi(LaporanKeuangan):
    """Laporan laba rugi operasional dari bunga, admin, denda, dan lelang."""

    def __init__(
        self,
        pendapatan_bunga: Decimal,
        pendapatan_admin: Decimal,
        denda: Decimal,
        biaya_perpanjangan: Decimal,
        kerugian_lelang: Decimal,
        rows: list[dict],
    ):
        self.pendapatan_bunga = pendapatan_bunga
        self.pendapatan_admin = pendapatan_admin
        self.denda = denda
        self.biaya_perpanjangan = biaya_perpanjangan
        self.kerugian_lelang = kerugian_lelang
        self.rows = rows

    @property
    def laba_bersih(self) -> Decimal:
        pendapatan = self.pendapatan_bunga + self.pendapatan_admin + self.denda + self.biaya_perpanjangan
        return pendapatan - self.kerugian_lelang

    def hasilkan(self) -> dict:
        return {
            "pendapatan_bunga": self.pendapatan_bunga,
            "pendapatan_admin": self.pendapatan_admin,
            "denda": self.denda,
            "biaya_perpanjangan": self.biaya_perpanjangan,
            "kerugian_lelang": self.kerugian_lelang,
            "laba_bersih": self.laba_bersih,
            "rows": self.rows,
        }


class LaporanAsetJaminan(LaporanKeuangan):
    """Laporan rekapitulasi status dan nilai agunan yang dipegang."""

    def __init__(self, items: list[dict]):
        self.items = items

    def hasilkan(self) -> list[dict]:
        return self.items
