"""Layanan Otentikasi, Pengelolaan Pengguna, dan RBAC."""
from pawn.errors import AksesDitolakError, DataTidakDitemukanError, ValidasiError
from pawn.models.pengguna import Pengguna, buat_pengguna
from pawn.repository.database import hash_password, verify_password
from pawn.repository.repos import PenggunaRepo, CabangRepo


class AuthService:
    """Mengelola otentikasi sesi, verifikasi sandi, dan perizinan berbasis peran."""

    def __init__(self, pengguna_repo: PenggunaRepo, cabang_repo: CabangRepo):
        self.pengguna_repo = pengguna_repo
        self.cabang_repo = cabang_repo

    def login(self, username: str, password: str) -> Pengguna:
        """Memvalidasi kredensial pengguna dan mengembalikan objek Pengguna polimorfis."""
        if not username or not password:
            raise ValidasiError("Username dan password tidak boleh kosong")

        row = self.pengguna_repo.get_by_username(username)
        if not row:
            raise AksesDitolakError("Username atau password salah")

        if int(row["aktif"]) != 1:
            raise AksesDitolakError("Akun pengguna sedang dinonaktifkan")

        if not verify_password(password, row["password_hash"], row["salt"]):
            raise AksesDitolakError("Username atau password salah")

        return buat_pengguna(row)

    def tambah_pengguna(
        self,
        username: str,
        password: str,
        nama: str,
        role: str,
        cabang_id: int | None,
    ) -> dict:
        """Mendaftarkan pengguna baru dengan validasi integritas."""
        username = (username or "").strip()
        nama = (nama or "").strip()
        role = (role or "").upper().strip()

        if not username or len(username) < 3:
            raise ValidasiError("Username minimal 3 karakter")
        if not password or len(password) < 6:
            raise ValidasiError("Password minimal 6 karakter")
        if not nama:
            raise ValidasiError("Nama pengguna tidak boleh kosong")
        if role not in ("ADMIN", "PETUGAS", "PENAKSIR"):
            raise ValidasiError(f"Role tidak valid: {role}. Harus ADMIN, PETUGAS, atau PENAKSIR")

        # Petugas dan Penaksir wajib terikat pada satu cabang
        if role != "ADMIN" and not cabang_id:
            raise ValidasiError("Petugas dan Penaksir wajib memiliki cabang operasional")

        if cabang_id is not None:
            cabang = self.cabang_repo.get(cabang_id)
            if not cabang:
                raise DataTidakDitemukanError(f"Cabang dengan ID {cabang_id} tidak ditemukan")

        existing = self.pengguna_repo.get_by_username(username)
        if existing:
            raise ValidasiError(f"Username '{username}' sudah digunakan")

        pw_hash, salt = hash_password(password)
        user_id = self.pengguna_repo.insert({
            "cabang_id": cabang_id,
            "username": username,
            "password_hash": pw_hash,
            "salt": salt,
            "role": role,
            "nama": nama,
            "aktif": 1,
        })

        return self.pengguna_repo.get(user_id)

    def ubah_aktif(self, user_id: int, aktif: int | bool) -> None:
        """Mengubah status aktif/nonaktif akun pengguna."""
        user = self.pengguna_repo.get(user_id)
        if not user:
            raise DataTidakDitemukanError(f"Pengguna dengan ID {user_id} tidak ditemukan")

        self.pengguna_repo.update(user_id, {"aktif": 1 if aktif else 0})

    def daftar_pengguna(self, cabang_id: int | None = None) -> list[dict]:
        """Mengambil daftar seluruh pengguna tanpa mengekspos hash/salt rahasia."""
        if cabang_id:
            rows = self.pengguna_repo.find(cabang_id=cabang_id)
        else:
            rows = self.pengguna_repo.all()

        hasil = []
        for r in rows:
            clean = dict(r)
            clean.pop("password_hash", None)
            clean.pop("salt", None)
            hasil.append(clean)
        return hasil
