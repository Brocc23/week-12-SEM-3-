"""Model Pengguna dan hierarki peran (RBAC)."""
from abc import ABC, abstractmethod


class Pengguna(ABC):
    """Kelas abstrak dasar untuk pengguna sistem."""

    def __init__(
        self,
        id: int | None,
        cabang_id: int | None,
        username: str,
        password_hash: str,
        salt: str,
        role: str,
        nama: str,
        aktif: int = 1,
    ):
        self.id = id
        self.cabang_id = cabang_id
        self.username = username
        self.nama = nama
        self.aktif = int(aktif)
        self.__password_hash = password_hash
        self.__salt = salt
        self.__role = role

    @property
    def role(self) -> str:
        return self.__role

    @property
    def password_hash(self) -> str:
        return self.__password_hash

    @property
    def salt(self) -> str:
        return self.__salt

    @abstractmethod
    def hak_akses(self) -> set[str]:
        """Mengembalikan himpunan izin (permissions) yang dimiliki pengguna."""
        pass

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cabang_id": self.cabang_id,
            "username": self.username,
            "role": self.__role,
            "nama": self.nama,
            "aktif": self.aktif,
        }


class Admin(Pengguna):
    """Administrator dengan akses penuh lintas cabang."""

    def __init__(self, id, cabang_id, username, password_hash, salt, nama, aktif=1):
        super().__init__(id, cabang_id, username, password_hash, salt, "ADMIN", nama, aktif)

    def hak_akses(self) -> set[str]:
        return {
            "admin",
            "nasabah.kelola",
            "taksir",
            "gadai",
            "bayar",
            "lelang",
            "laporan",
        }


class Petugas(Pengguna):
    """Petugas operasional cabang untuk pendaftaran, gadai, kasir, dan laporan."""

    def __init__(self, id, cabang_id, username, password_hash, salt, nama, aktif=1):
        super().__init__(id, cabang_id, username, password_hash, salt, "PETUGAS", nama, aktif)

    def hak_akses(self) -> set[str]:
        return {
            "nasabah.kelola",
            "gadai",
            "bayar",
            "laporan",
        }


class Penaksir(Pengguna):
    """Penaksir barang jaminan bersertifikat."""

    def __init__(self, id, cabang_id, username, password_hash, salt, nama, aktif=1):
        super().__init__(id, cabang_id, username, password_hash, salt, "PENAKSIR", nama, aktif)

    def hak_akses(self) -> set[str]:
        return {
            "taksir",
        }


def buat_pengguna(data: dict) -> Pengguna:
    """Factory helper untuk membuat instance turunan Pengguna sesuai role."""
    role = (data.get("role") or "").upper()
    kwargs = {
        "id": data.get("id"),
        "cabang_id": data.get("cabang_id"),
        "username": data.get("username"),
        "password_hash": data.get("password_hash", ""),
        "salt": data.get("salt", ""),
        "nama": data.get("nama", ""),
        "aktif": data.get("aktif", 1),
    }
    if role == "ADMIN":
        return Admin(**kwargs)
    elif role == "PETUGAS":
        return Petugas(**kwargs)
    elif role == "PENAKSIR":
        return Penaksir(**kwargs)
    raise ValueError(f"Role tidak dikenal: {role}")
