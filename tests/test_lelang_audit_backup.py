"""Tests for Overdue Detection, Auction Stages, Audit Immutability, and Backup/Restore."""

from datetime import date, timedelta
from decimal import Decimal
import os
import sqlite3
import unittest
from pawn.errors import AksesDitolakError, AturanBisnisError
from tests.base import BaseTestCase


class TestLelangAuditBackup(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.login("admin", "admin123")
        self.nasabah = self.app.daftar_nasabah()[0]

    def _setup_overdue_loan(self) -> str:
        """Helper to create a loan and simulate it becoming overdue past grace period."""
        today = date.today()
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Emas Batangan 10gr",
            atribut={"berat": 10, "kadar": 24},
            jumlah_pinjaman=5000000,
            tenor_hari=120,
        )
        # Advance 125 days (overdue by 5 days)
        self.app.set_tanggal_simulasi(today + timedelta(days=125))
        self.app.deteksi_jatuh_tempo()
        return loan["no_kontrak"]

    def test_overdue_detection(self):
        no_kontrak = self._setup_overdue_loan()
        det = self.app.detail_pinjaman(no_kontrak)
        self.assertEqual(det["status"], "JATUH_TEMPO")

    def test_auction_grace_period(self):
        no_kontrak = self._setup_overdue_loan()
        # Overdue by 5 days; grace period is 14 days, so notice must be rejected
        with self.assertRaises(AturanBisnisError):
            self.app.kirim_notifikasi_lelang(no_kontrak)

    def test_auction_stages_progression(self):
        today = date.today()
        no_kontrak = self._setup_overdue_loan()

        # Advance past grace period (140 days > 120 + 14)
        self.app.set_tanggal_simulasi(today + timedelta(days=140))

        # Tahap 1
        n1 = self.app.kirim_notifikasi_lelang(no_kontrak)
        self.assertEqual(n1["tahap"], 1)

        # Cannot start auction before Tahap 2 is completed
        with self.assertRaises(AturanBisnisError):
            self.app.mulai_proses_lelang(no_kontrak)

        # Tahap 2
        n2 = self.app.kirim_notifikasi_lelang(no_kontrak)
        self.assertEqual(n2["tahap"], 2)

        # Stage 3 notice must be rejected (max 2 stages)
        with self.assertRaises(AturanBisnisError):
            self.app.kirim_notifikasi_lelang(no_kontrak)

        # Starting auction now succeeds
        res = self.app.mulai_proses_lelang(no_kontrak)
        self.assertEqual(res["status"], "DALAM_PROSES_LELANG")

    def test_auction_resolution_surplus(self):
        today = date.today()
        no_kontrak = self._setup_overdue_loan()
        self.app.set_tanggal_simulasi(today + timedelta(days=140))
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.mulai_proses_lelang(no_kontrak)

        kewajiban = self.app.hitung_kewajiban(no_kontrak)["total"]
        # Auction price > kewajiban -> SURPLUS
        harga_lelang = kewajiban + Decimal("1500000")
        res = self.app.selesaikan_lelang(no_kontrak, harga_lelang)

        self.assertEqual(res["hasil"], "SURPLUS")
        self.assertEqual(res["hak_nasabah"], Decimal("1500000"))
        self.assertEqual(res["kerugian"], Decimal("0"))
        self.assertEqual(res["selisih"], Decimal("1500000"))

    def test_auction_resolution_impas(self):
        today = date.today()
        no_kontrak = self._setup_overdue_loan()
        self.app.set_tanggal_simulasi(today + timedelta(days=140))
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.mulai_proses_lelang(no_kontrak)

        kewajiban = self.app.hitung_kewajiban(no_kontrak)["total"]
        # Auction price == kewajiban -> IMPAS
        res = self.app.selesaikan_lelang(no_kontrak, kewajiban)

        self.assertEqual(res["hasil"], "IMPAS")
        self.assertEqual(res["hak_nasabah"], Decimal("0"))
        self.assertEqual(res["kerugian"], Decimal("0"))
        self.assertEqual(res["selisih"], Decimal("0"))

    def test_auction_resolution_defisit(self):
        today = date.today()
        no_kontrak = self._setup_overdue_loan()
        self.app.set_tanggal_simulasi(today + timedelta(days=140))
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.kirim_notifikasi_lelang(no_kontrak)
        self.app.mulai_proses_lelang(no_kontrak)

        kewajiban = self.app.hitung_kewajiban(no_kontrak)["total"]
        # Auction price < kewajiban -> DEFISIT
        harga_lelang = kewajiban - Decimal("800000")
        res = self.app.selesaikan_lelang(no_kontrak, harga_lelang)

        self.assertEqual(res["hasil"], "DEFISIT")
        self.assertEqual(res["hak_nasabah"], Decimal("0"))
        self.assertEqual(res["kerugian"], Decimal("800000"))
        self.assertEqual(res["selisih"], Decimal("-800000"))

    def test_audit_log_immutability(self):
        # Insert test audit log
        log_id = self.app.audit_repo.insert({
            "waktu": "2026-11-12 10:00:00",
            "pengguna_id": 1,
            "aksi": "TEST_AUDIT",
            "detail": "Catatan integritas",
        })

        # 1. Python repo layer raises PermissionError
        with self.assertRaises(PermissionError):
            self.app.audit_repo.update(log_id, {"detail": "Modifikasi"})

        with self.assertRaises(PermissionError):
            self.app.audit_repo.delete(log_id)

        # 2. SQLite DB trigger aborts direct UPDATE and DELETE
        with self.assertRaises(sqlite3.Error):
            self.app.db.connection().execute(
                "UPDATE audit_log SET detail = ? WHERE id = ?", ("Manipulasi", log_id)
            )

        with self.assertRaises(sqlite3.Error):
            self.app.db.connection().execute(
                "DELETE FROM audit_log WHERE id = ?", (log_id,)
            )

    def test_backup_and_restore_database(self):
        backup_file = os.path.join(self.tmpdir, "backup_test.db")
        self.app.backup_database(backup_file)
        self.assertTrue(os.path.exists(backup_file))

        # Add a new branch after backup
        self.app.tambah_cabang("SMG", "Cabang Semarang", "Jl. Pandanaran No. 1")
        branches_before_restore = [c["kode"] for c in self.app.daftar_cabang()]
        self.assertIn("SMG", branches_before_restore)

        # Restore from backup
        self.app.restore_database(backup_file)
        self.app.login("admin", "admin123")  # Re-authenticate after restore
        branches_after_restore = [c["kode"] for c in self.app.daftar_cabang()]
        self.assertNotIn("SMG", branches_after_restore)

    def test_backup_restore_rbac_non_admin_denied(self):
        self.app.login("petugas1", "petugas123")
        backup_file = os.path.join(self.tmpdir, "backup_petugas.db")
        with self.assertRaises(AksesDitolakError):
            self.app.backup_database(backup_file)
        with self.assertRaises(AksesDitolakError):
            self.app.restore_database(backup_file)


if __name__ == "__main__":
    unittest.main()
