"""Tests for Customer (Nasabah) management, validations, and constraints."""

import unittest
from pawn.errors import AturanBisnisError, ValidasiError
from tests.base import BaseTestCase


class TestNasabah(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.login("admin", "admin123")

    def test_tambah_nasabah_success(self):
        res = self.app.tambah_nasabah(
            nik="3171099999990001",
            nama="Budi Wicaksono",
            alamat="Jl. Rasuna Said No. 5",
            telepon="081122334455",
            email="budi.w@example.com",
        )
        self.assertIsNotNone(res["id"])
        self.assertEqual(res["nik"], "3171099999990001")
        self.assertEqual(res["nama"], "Budi Wicaksono")
        self.assertEqual(res["status"], "AKTIF")

    def test_nik_uniqueness(self):
        # NIK 3171012345670001 is already in seed
        with self.assertRaises(ValidasiError):
            self.app.tambah_nasabah(
                nik="3171012345670001",
                nama="Orang Baru NIK Sama",
                alamat="Jl. Baru",
                telepon="081299998888",
                email="baru@example.com",
            )

    def test_phone_validation(self):
        with self.assertRaises(ValidasiError):
            self.app.tambah_nasabah(
                nik="3171099999990002",
                nama="Nasabah Tanpa Telepon",
                alamat="Jl. Salemba",
                telepon="",  # Empty phone
                email="tanpa.telp@example.com",
            )

    def test_nik_format_validation(self):
        # NIK too short (< 8 chars)
        with self.assertRaises(ValidasiError):
            self.app.tambah_nasabah(
                nik="123",
                nama="Nasabah NIK Pendek",
                alamat="Jl. Salemba",
                telepon="0812345678",
                email="pendek@example.com",
            )

    def test_nasabah_deletion_blocked_with_active_loan(self):
        # Register a new customer and submit a loan
        cust = self.app.tambah_nasabah(
            nik="3171099999990003",
            nama="Nasabah Aktif Pinjam",
            alamat="Jl. Gatot Subroto",
            telepon="081234567890",
            email="aktif@example.com",
        )
        self.app.ajukan_gadai(
            nasabah_id=cust["id"],
            jenis="EMAS",
            deskripsi="Kalung Emas 10gr",
            atribut={"berat": 10, "kadar": 24},
            jumlah_pinjaman=5000000,
        )

        # Attempting deletion while loan is ACTIVE must be rejected
        with self.assertRaises(AturanBisnisError):
            self.app.hapus_nasabah(cust["id"])

        # Customer must still exist
        found = self.app.nasabah_repo.get(cust["id"])
        self.assertIsNotNone(found)

    def test_nasabah_deletion_without_loans_succeeds(self):
        cust = self.app.tambah_nasabah(
            nik="3171099999990004",
            nama="Nasabah Tanpa Pinjaman",
            alamat="Jl. Thamrin",
            telepon="081234567899",
            email="tanpa.pinjam@example.com",
        )
        # Deletion succeeds because no foreign keys reference this customer
        self.app.hapus_nasabah(cust["id"])
        found = self.app.nasabah_repo.get(cust["id"])
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
