"""Tests for Authentication, RBAC, password hashing, and branch isolation."""

import unittest
from pawn.errors import AksesDitolakError, PawnError
from pawn.repository.database import verify_password
from tests.base import BaseTestCase


class TestAuthRBAC(BaseTestCase):

    def test_login_success_and_logout(self):
        user = self.app.login("admin", "admin123")
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["role"], "ADMIN")
        self.assertIsNotNone(self.app.pengguna_aktif)

        self.app.logout()
        self.assertIsNone(self.app.pengguna_aktif)

    def test_login_invalid_password(self):
        with self.assertRaises(PawnError):
            self.app.login("admin", "wrong_pass")
        self.assertIsNone(self.app.pengguna_aktif)

    def test_login_nonexistent_user(self):
        with self.assertRaises(PawnError):
            self.app.login("ghost_user", "some_pass")
        self.assertIsNone(self.app.pengguna_aktif)

    def test_unauthenticated_access_denied(self):
        # Attempting calling protected methods without prior login
        with self.assertRaises(AksesDitolakError):
            self.app.daftar_pengguna()
        with self.assertRaises(AksesDitolakError):
            self.app.daftar_cabang()
        with self.assertRaises(AksesDitolakError):
            self.app.daftar_nasabah()

    def test_rbac_petugas_cannot_access_admin(self):
        self.app.login("petugas1", "petugas123")
        with self.assertRaises(AksesDitolakError):
            self.app.daftar_pengguna()
        with self.assertRaises(AksesDitolakError):
            self.app.tambah_cabang("SBY", "Cabang Surabaya", "Jl. Basuki")
        with self.assertRaises(AksesDitolakError):
            self.app.ubah_parameter("harga_emas_per_gram", "1500000")
        with self.assertRaises(AksesDitolakError):
            self.app.lihat_audit_log()

    def test_rbac_petugas_cannot_taksir(self):
        self.app.login("petugas1", "petugas123")
        with self.assertRaises(AksesDitolakError):
            self.app.hitung_taksiran("EMAS", {"berat": 10, "kadar": 24})

    def test_rbac_penaksir_cannot_gadai_and_bayar(self):
        self.app.login("penaksir1", "penaksir123")
        with self.assertRaises(AksesDitolakError):
            self.app.ajukan_gadai(1, "EMAS", "Cincin", {"berat": 5, "kadar": 24}, 1000000)
        with self.assertRaises(AksesDitolakError):
            self.app.bayar_angsuran("GDI-JKT-DUMMY", 100000, "TUNAI")

    def test_password_hashing_not_plain(self):
        self.app.login("admin", "admin123")
        users = self.app.pengguna_repo.all()
        self.assertTrue(len(users) >= 5)
        for u in users:
            # Hash must NOT be plain text
            self.assertNotEqual(u["password_hash"], "admin123")
            self.assertNotEqual(u["password_hash"], "petugas123")
            self.assertNotEqual(u["password_hash"], "penaksir123")
            # 64 hex characters for SHA-256
            self.assertEqual(len(u["password_hash"]), 64)
            # Salt must be 32 hex characters
            self.assertEqual(len(u["salt"]), 32)

        admin = self.app.pengguna_repo.get_by_username("admin")
        self.assertTrue(verify_password("admin123", admin["password_hash"], admin["salt"]))
        self.assertFalse(verify_password("wrong", admin["password_hash"], admin["salt"]))

    def test_cabang_isolation(self):
        # Petugas 1 belongs to Cabang 1 (JKT)
        self.app.login("petugas1", "petugas123")
        nasabah_jkt = self.app.daftar_nasabah()
        self.assertTrue(len(nasabah_jkt) > 0)
        for n in nasabah_jkt:
            self.assertEqual(n["cabang_id"], 1)

        # Petugas 2 belongs to Cabang 2 (BDG)
        self.app.login("petugas2", "petugas123")
        nasabah_bdg = self.app.daftar_nasabah()
        self.assertTrue(len(nasabah_bdg) > 0)
        for n in nasabah_bdg:
            self.assertEqual(n["cabang_id"], 2)

        # Admin has no branch isolation and sees all
        self.app.login("admin", "admin123")
        nasabah_all = self.app.daftar_nasabah()
        cabang_ids = {n["cabang_id"] for n in nasabah_all}
        self.assertIn(1, cabang_ids)
        self.assertIn(2, cabang_ids)


if __name__ == "__main__":
    unittest.main()
