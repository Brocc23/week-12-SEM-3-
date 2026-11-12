"""Model Pinjaman, Perpanjangan, Gudang, Notifikasi Lelang, dan Lelang."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


class Pinjaman:
    """Entitas kontrak pinjaman gadai dengan enkapsulasi saldo."""

    def __init__(
        self,
        id: int | None,
        no_kontrak: str,
        cabang_id: int,
        nasabah_id: int,
        barang_id: int,
        petugas_id: int,
        penaksir_id: int,
        nilai_taksiran: Decimal | str | int,
        persen_pinjaman: Decimal | str,
        pokok: Decimal | str | int,
        sisa_pokok: Decimal | str | int,
        bunga_terutang: Decimal | str | int = 0,
        biaya_admin_terutang: Decimal | str | int = 0,
        denda_terutang: Decimal | str | int = 0,
        suku_bunga_periode: Decimal | str = "0.012",
        tgl_transaksi: date | str = None,
        tgl_jatuh_tempo: date | str = None,
        jumlah_perpanjangan: int = 0,
        status: str = "AKTIF",
    ):
        self.id = id
        self.no_kontrak = no_kontrak
        self.cabang_id = cabang_id
        self.nasabah_id = nasabah_id
        self.barang_id = barang_id
        self.petugas_id = petugas_id
        self.penaksir_id = penaksir_id
        self.persen_pinjaman = Decimal(str(persen_pinjaman))
        self.tgl_transaksi = tgl_transaksi if isinstance(tgl_transaksi, date) else date.fromisoformat(str(tgl_transaksi))
        self.tgl_jatuh_tempo = tgl_jatuh_tempo if isinstance(tgl_jatuh_tempo, date) else date.fromisoformat(str(tgl_jatuh_tempo))
        self.jumlah_perpanjangan = int(jumlah_perpanjangan)

        # Enkapsulasi data sensitif
        self.__nilai_taksiran = Decimal(str(nilai_taksiran)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__pokok = Decimal(str(pokok)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__sisa_pokok = Decimal(str(sisa_pokok)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__bunga_terutang = Decimal(str(bunga_terutang or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__biaya_admin_terutang = Decimal(str(biaya_admin_terutang or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__denda_terutang = Decimal(str(denda_terutang or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__suku_bunga_periode = Decimal(str(suku_bunga_periode))
        self.__status = status

    # Properti Getter
    @property
    def nilai_taksiran(self) -> Decimal:
        return self.__nilai_taksiran

    @property
    def pokok(self) -> Decimal:
        return self.__pokok

    @property
    def sisa_pokok(self) -> Decimal:
        return self.__sisa_pokok

    @property
    def bunga_terutang(self) -> Decimal:
        return self.__bunga_terutang

    @bunga_terutang.setter
    def bunga_terutang(self, val: Decimal | str | int):
        self.__bunga_terutang = Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def biaya_admin_terutang(self) -> Decimal:
        return self.__biaya_admin_terutang

    @biaya_admin_terutang.setter
    def biaya_admin_terutang(self, val: Decimal | str | int):
        self.__biaya_admin_terutang = Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def denda_terutang(self) -> Decimal:
        return self.__denda_terutang

    @denda_terutang.setter
    def denda_terutang(self, val: Decimal | str | int):
        self.__denda_terutang = Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def suku_bunga_periode(self) -> Decimal:
        return self.__suku_bunga_periode

    @property
    def status(self) -> str:
        return self.__status

    @status.setter
    def status(self, val: str):
        status_valid = {"AKTIF", "JATUH_TEMPO", "DALAM_PROSES_LELANG", "LUNAS", "TERLELANG", "DIKEMBALIKAN"}
        if val not in status_valid:
            raise ValueError(f"Status pinjaman tidak valid: {val}")
        self.__status = val

    def sinkronkan_bunga_dan_denda(
        self,
        hari_ini: date,
        denda_per_hari: Decimal,
        bunga_dibayar: Decimal = Decimal("0"),
        denda_dibayar: Decimal = Decimal("0"),
    ):
        """Menghitung akrual bunga dan denda hari berjalan dikurangi pembayaran yang telah diterima."""
        if self.__status in ("LUNAS", "TERLELANG", "DIKEMBALIKAN"):
            return

        # Bunga: B = P * i * t (periode 15 hari, dibulatkan ke atas, min 1 periode)
        hari_berjalan = max(1, (hari_ini - self.tgl_transaksi).days)
        periode = (hari_berjalan + 14) // 15
        total_bunga = (self.__sisa_pokok * self.__suku_bunga_periode * Decimal(periode)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__bunga_terutang = max(Decimal("0"), total_bunga - bunga_dibayar)

        # Denda jika lewat jatuh tempo
        if hari_ini > self.tgl_jatuh_tempo:
            hari_terlambat = (hari_ini - self.tgl_jatuh_tempo).days
            total_denda = (self.__sisa_pokok * denda_per_hari * Decimal(hari_terlambat)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            self.__denda_terutang = max(Decimal("0"), total_denda - denda_dibayar)
        else:
            self.__denda_terutang = Decimal("0")

    def hitung_total_kewajiban(self) -> Decimal:
        """Total kewajiban = biaya_admin + denda + bunga + sisa_pokok."""
        return self.__biaya_admin_terutang + self.__denda_terutang + self.__bunga_terutang + self.__sisa_pokok

    def terapkan_pembayaran(self, jumlah: Decimal) -> dict:
        """
        Waterfall alokasi pembayaran:
        1. Biaya Admin
        2. Denda Keterlambatan
        3. Bunga Terutang
        4. Sisa Pokok Pinjaman
        """
        sisa_dana = Decimal(str(jumlah)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if sisa_dana <= Decimal("0"):
            raise ValueError("Nominal pembayaran harus lebih dari 0")

        # 1. Alokasi Biaya Admin
        bayar_admin = min(self.__biaya_admin_terutang, sisa_dana)
        self.__biaya_admin_terutang -= bayar_admin
        sisa_dana -= bayar_admin

        # 2. Alokasi Denda
        bayar_denda = min(self.__denda_terutang, sisa_dana)
        self.__denda_terutang -= bayar_denda
        sisa_dana -= bayar_denda

        # 3. Alokasi Bunga
        bayar_bunga = min(self.__bunga_terutang, sisa_dana)
        self.__bunga_terutang -= bayar_bunga
        sisa_dana -= bayar_bunga

        # 4. Alokasi Pokok
        bayar_pokok = min(self.__sisa_pokok, sisa_dana)
        self.__sisa_pokok -= bayar_pokok
        sisa_dana -= bayar_pokok

        # Cek apakah lunas
        if (
            self.__sisa_pokok == Decimal("0")
            and self.__bunga_terutang == Decimal("0")
            and self.__denda_terutang == Decimal("0")
            and self.__biaya_admin_terutang == Decimal("0")
        ):
            self.__status = "LUNAS"

        return {
            "bayar_admin": bayar_admin,
            "bayar_denda": bayar_denda,
            "bayar_bunga": bayar_bunga,
            "bayar_pokok": bayar_pokok,
            "kembalian": sisa_dana,
            "sisa_pokok": self.__sisa_pokok,
            "status": self.__status,
        }

    def perpanjang_jatuh_tempo(self, tgl_baru: date):
        """Memperbarui tanggal jatuh tempo dan mencatat penambahan perpanjangan."""
        self.tgl_jatuh_tempo = tgl_baru
        self.jumlah_perpanjangan += 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "no_kontrak": self.no_kontrak,
            "cabang_id": self.cabang_id,
            "nasabah_id": self.nasabah_id,
            "barang_id": self.barang_id,
            "petugas_id": self.petugas_id,
            "penaksir_id": self.penaksir_id,
            "nilai_taksiran": self.__nilai_taksiran,
            "persen_pinjaman": self.persen_pinjaman,
            "pokok": self.__pokok,
            "sisa_pokok": self.__sisa_pokok,
            "bunga_terutang": self.__bunga_terutang,
            "biaya_admin_terutang": self.__biaya_admin_terutang,
            "denda_terutang": self.__denda_terutang,
            "suku_bunga_periode": self.__suku_bunga_periode,
            "tgl_transaksi": str(self.tgl_transaksi),
            "tgl_jatuh_tempo": str(self.tgl_jatuh_tempo),
            "jumlah_perpanjangan": self.jumlah_perpanjangan,
            "status": self.__status,
        }


@dataclass
class Perpanjangan:
    """Catatan riwayat perpanjangan tenor pinjaman."""
    id: int | None
    pinjaman_id: int
    tgl_lama: date | str
    tgl_baru: date | str
    biaya: Decimal
    waktu: str
    petugas_id: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pinjaman_id": self.pinjaman_id,
            "tgl_lama": str(self.tgl_lama),
            "tgl_baru": str(self.tgl_baru),
            "biaya": self.biaya,
            "waktu": self.waktu,
            "petugas_id": self.petugas_id,
        }


@dataclass
class Gudang:
    """Penyimpanan dan inventarisasi fisik barang jaminan di gudang/khasanah."""
    id: int | None
    kode_barang: str
    barang_id: int
    pinjaman_id: int
    lokasi: str
    tgl_masuk: date | str
    kondisi: str
    petugas_id: int
    status: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kode_barang": self.kode_barang,
            "barang_id": self.barang_id,
            "pinjaman_id": self.pinjaman_id,
            "lokasi": self.lokasi,
            "tgl_masuk": str(self.tgl_masuk),
            "kondisi": self.kondisi,
            "petugas_id": self.petugas_id,
            "status": self.status,
        }


@dataclass
class NotifikasiLelang:
    """Surat peringatan dan notifikasi tahapan lelang kepada nasabah."""
    id: int | None
    pinjaman_id: int
    tahap: int
    tanggal: date | str
    pesan: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pinjaman_id": self.pinjaman_id,
            "tahap": self.tahap,
            "tanggal": str(self.tanggal),
            "pesan": self.pesan,
        }


@dataclass
class Lelang:
    """Penyelesaian eksekusi lelang agunan yang wanprestasi."""
    id: int | None
    pinjaman_id: int
    harga_lelang: Decimal
    total_kewajiban: Decimal
    selisih: Decimal
    hasil: str  # SURPLUS / IMPAS / DEFISIT
    hak_nasabah: Decimal
    kerugian: Decimal
    tanggal: date | str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pinjaman_id": self.pinjaman_id,
            "harga_lelang": self.harga_lelang,
            "total_kewajiban": self.total_kewajiban,
            "selisih": self.selisih,
            "hasil": self.hasil,
            "hak_nasabah": self.hak_nasabah,
            "kerugian": self.kerugian,
            "tanggal": str(self.tanggal),
        }
