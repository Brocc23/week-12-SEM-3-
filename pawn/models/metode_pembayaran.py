"""Model Metode Pembayaran dengan abstraksi dan polimorfisme."""
from abc import ABC, abstractmethod
from decimal import Decimal


class MetodePembayaran(ABC):
    """Kelas abstrak dasar untuk metode pembayaran."""

    def __init__(self, kode: str, nama: str):
        self.kode = kode
        self.nama = nama

    @abstractmethod
    def proses(self, jumlah: Decimal) -> bool:
        """Memvalidasi dan memproses pembayaran dengan nominal tertentu."""
        pass

    @abstractmethod
    def hitung_biaya(self, jumlah: Decimal) -> Decimal:
        """Menghitung biaya transaksi metode pembayaran (bila ada)."""
        pass


class Tunai(MetodePembayaran):
    """Pembayaran tunai di kasir cabang."""

    def __init__(self):
        super().__init__("TUNAI", "Tunai di Kasir")

    def proses(self, jumlah: Decimal) -> bool:
        if jumlah <= Decimal("0"):
            raise ValueError("Nominal tunai harus lebih dari 0")
        return True

    def hitung_biaya(self, jumlah: Decimal) -> Decimal:
        return Decimal("0")


class TransferBank(MetodePembayaran):
    """Pembayaran transfer virtual account / rekening bank."""

    def __init__(self):
        super().__init__("TRANSFER", "Transfer Bank")

    def proses(self, jumlah: Decimal) -> bool:
        if jumlah < Decimal("10000"):
            raise ValueError("Minimal pembayaran transfer bank adalah Rp 10.000")
        return True

    def hitung_biaya(self, jumlah: Decimal) -> Decimal:
        return Decimal("0")


class QRIS(MetodePembayaran):
    """Pembayaran scan QRIS nasional."""

    def __init__(self):
        super().__init__("QRIS", "QRIS Dinamis")

    def proses(self, jumlah: Decimal) -> bool:
        if jumlah <= Decimal("0"):
            raise ValueError("Nominal QRIS harus lebih dari 0")
        # Batas maksimal per transaksi QRIS regulasi BI Rp 10.000.000
        if jumlah > Decimal("10000000"):
            raise ValueError("Nominal transaksi QRIS maksimal Rp 10.000.000")
        return True

    def hitung_biaya(self, jumlah: Decimal) -> Decimal:
        return Decimal("0")


class DompetDigital(MetodePembayaran):
    """Pembayaran melalui e-wallet (GoPay, OVO, Dana, ShopeePay)."""

    def __init__(self):
        super().__init__("EWALLET", "Dompet Digital (E-Wallet)")

    def proses(self, jumlah: Decimal) -> bool:
        if jumlah < Decimal("5000"):
            raise ValueError("Minimal transaksi e-wallet adalah Rp 5.000")
        if jumlah > Decimal("20000000"):
            raise ValueError("Maksimal saldo transaksi e-wallet adalah Rp 20.000.000")
        return True

    def hitung_biaya(self, jumlah: Decimal) -> Decimal:
        return Decimal("0")


def dapatkan_metode_pembayaran(kode: str) -> MetodePembayaran:
    """Factory helper untuk mendapatkan instans MetodePembayaran dari kodenya."""
    k = (kode or "TUNAI").upper()
    if k == "TUNAI":
        return Tunai()
    elif k in ("TRANSFER", "TRANSFER_BANK", "BANK"):
        return TransferBank()
    elif k == "QRIS":
        return QRIS()
    elif k in ("EWALLET", "DOMPET_DIGITAL"):
        return DompetDigital()
    raise ValueError(f"Metode pembayaran tidak didukung: {kode}")
