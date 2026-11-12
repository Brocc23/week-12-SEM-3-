"""Layanan Pencatatan Audit Log dan Pembukuan Jurnal Akuntansi."""
from decimal import Decimal
from pawn.repository.repos import AuditRepo, JurnalRepo


class AuditService:
    """Mengelola catatan audit jejak aktivitas pengguna dan jurnal akuntansi."""

    def __init__(self, audit_repo: AuditRepo, jurnal_repo: JurnalRepo):
        self.audit_repo = audit_repo
        self.jurnal_repo = jurnal_repo

    def catat_audit(
        self,
        pengguna_id: int | None,
        aksi: str,
        detail: str,
        waktu: str,
    ) -> int:
        """Menyimpan log audit yang bersifat immutable (kebal modifikasi/penghapusan)."""
        return self.audit_repo.insert({
            "waktu": waktu,
            "pengguna_id": pengguna_id,
            "aksi": aksi,
            "detail": detail,
        })

    def lihat_audit_log(self, limit: int = 500) -> list[dict]:
        """Mengambil riwayat log audit terbaru."""
        sql = """
            SELECT a.id, a.waktu, a.pengguna_id, u.username, u.nama as nama_pengguna, a.aksi, a.detail
            FROM audit_log a
            LEFT JOIN pengguna u ON a.pengguna_id = u.id
            ORDER BY a.id DESC
            LIMIT ?
        """
        return self.audit_repo.query(sql, (limit,))

    def catat_jurnal(
        self,
        waktu: str,
        no_ref: str,
        akun: str,
        debit: Decimal | str | int = 0,
        kredit: Decimal | str | int = 0,
        keterangan: str = "",
    ) -> int:
        """Mencatat transaksi debit/kredit pada buku jurnal umum."""
        return self.jurnal_repo.insert({
            "waktu": waktu,
            "no_ref": no_ref,
            "akun": akun,
            "debit": Decimal(str(debit or 0)),
            "kredit": Decimal(str(kredit or 0)),
            "keterangan": keterangan,
        })
