"""Model Audit Log dan Pembukuan Jurnal Akuntansi."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class AuditLog:
    """Catatan audit jejak aktivitas sistem yang bersifat immutable."""
    id: int | None
    waktu: str
    pengguna_id: int | None
    aksi: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "waktu": self.waktu,
            "pengguna_id": self.pengguna_id,
            "aksi": self.aksi,
            "detail": self.detail,
        }


class Jurnal:
    """Entitas entri jurnal umum akuntansi pegadaian."""

    def __init__(
        self,
        id: int | None,
        waktu: str,
        no_ref: str,
        akun: str,
        debit: Decimal | str | int = 0,
        kredit: Decimal | str | int = 0,
        keterangan: str = "",
    ):
        self.id = id
        self.waktu = waktu
        self.no_ref = no_ref
        self.akun = akun
        self.__debit = Decimal(str(debit or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.__kredit = Decimal(str(kredit or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.keterangan = keterangan

    @property
    def debit(self) -> Decimal:
        return self.__debit

    @property
    def kredit(self) -> Decimal:
        return self.__kredit

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "waktu": self.waktu,
            "no_ref": self.no_ref,
            "akun": self.akun,
            "debit": self.__debit,
            "kredit": self.__kredit,
            "keterangan": self.keterangan,
        }
