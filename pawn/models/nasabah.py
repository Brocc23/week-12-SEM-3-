"""Model Nasabah Pegadaian."""
from dataclasses import dataclass
from datetime import date


@dataclass
class Nasabah:
    """Entitas nasabah pemilik agunan dan penerima pinjaman."""
    id: int | None
    cabang_id: int
    kode: str
    nik: str
    nama: str
    alamat: str
    telepon: str
    email: str
    tgl_daftar: date | str
    status: str = "AKTIF"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cabang_id": self.cabang_id,
            "kode": self.kode,
            "nik": self.nik,
            "nama": self.nama,
            "alamat": self.alamat,
            "telepon": self.telepon,
            "email": self.email,
            "tgl_daftar": str(self.tgl_daftar),
            "status": self.status,
        }
