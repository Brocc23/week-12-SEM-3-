"""Model Cabang Pegadaian."""
from dataclasses import dataclass


@dataclass
class Cabang:
    """Entitas cabang operasional pegadaian."""
    id: int | None
    kode: str
    nama: str
    alamat: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kode": self.kode,
            "nama": self.nama,
            "alamat": self.alamat,
        }
