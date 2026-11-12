"""Tests for the 4 appraisal formulas (EMAS, KENDARAAN, ELEKTRONIK, LAPTOP)."""

from decimal import Decimal
import unittest
from pawn.errors import ValidasiError
from tests.base import BaseTestCase


class TestPenaksiran(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.login("penaksir1", "penaksir123")

    def test_formula_emas(self):
        # Formula: T = berat * (kadar / 24) * harga_emas_per_gram (1,000,000)
        # LTV = 0.90
        res1 = self.app.hitung_taksiran("EMAS", {"berat": 10, "kadar": 24})
        self.assertEqual(res1["nilai_taksiran"], Decimal("10000000"))
        self.assertEqual(res1["maks_pinjaman"], Decimal("9000000"))

        res2 = self.app.hitung_taksiran("EMAS", {"berat": 12, "kadar": 18})
        # 12 * (18/24) * 1,000,000 = 9,000,000; Pmax = 9,000,000 * 0.9 = 8,100,000
        self.assertEqual(res2["nilai_taksiran"], Decimal("9000000"))
        self.assertEqual(res2["maks_pinjaman"], Decimal("8100000"))

    def test_formula_kendaraan(self):
        # Formula: T = Hp * Fu * Fk
        # Fu = max(0.3, 1.0 - 0.07 * umur), Fk: BAIK=1.0, CUKUP=0.8, BURUK=0.6, LTV = 0.75
        res1 = self.app.hitung_taksiran("KENDARAAN", {
            "harga_pasar": 20000000,
            "umur": 2,
            "kondisi": "BAIK",
        })
        # Fu = 1.0 - 0.14 = 0.86; T = 20M * 0.86 * 1.0 = 17,200,000; Pmax = 17.2M * 0.75 = 12,900,000
        self.assertEqual(res1["nilai_taksiran"], Decimal("17200000"))
        self.assertEqual(res1["maks_pinjaman"], Decimal("12900000"))

        # Test age floor clamp (min 0.3)
        res2 = self.app.hitung_taksiran("KENDARAAN", {
            "harga_pasar": 30000000,
            "umur": 15,
            "kondisi": "CUKUP",
        })
        # Fu = max(0.3, 1 - 0.07*15 = -0.05) = 0.3; Fk = 0.8; T = 30M * 0.3 * 0.8 = 7,200,000
        self.assertEqual(res2["nilai_taksiran"], Decimal("7200000"))
        self.assertEqual(res2["maks_pinjaman"], Decimal("5400000"))

    def test_formula_elektronik(self):
        # Formula: T = Hp * ((1 - 0.15) ** umur) * Fk; LTV = 0.60
        res1 = self.app.hitung_taksiran("ELEKTRONIK", {
            "harga_pasar": 10000000,
            "umur": 1,
            "kondisi": "BAIK",
        })
        # T = 10M * 0.85 * 1.0 = 8,500,000; Pmax = 8.5M * 0.6 = 5,100,000
        self.assertEqual(res1["nilai_taksiran"], Decimal("8500000"))
        self.assertEqual(res1["maks_pinjaman"], Decimal("5100000"))

        res2 = self.app.hitung_taksiran("ELEKTRONIK", {
            "harga_pasar": 10000000,
            "umur": 2,
            "kondisi": "CUKUP",
        })
        # T = 10M * 0.7225 * 0.8 = 5,780,000; Pmax = 5.78M * 0.6 = 3,468,000
        self.assertEqual(res1["nilai_taksiran"], Decimal("8500000"))
        self.assertEqual(res2["nilai_taksiran"], Decimal("5780000"))
        self.assertEqual(res2["maks_pinjaman"], Decimal("3468000"))

    def test_formula_laptop(self):
        # Formula: T = Hp * Fs * Fu * Fk
        # Fs: LOW=0.7, MID=1.0, HIGH=1.2; Fu = max(0.2, 1.0 - 0.12 * umur); LTV = 0.60
        res1 = self.app.hitung_taksiran("LAPTOP", {
            "harga_pasar": 10000000,
            "spesifikasi": "MID",
            "umur": 1,
            "kondisi": "BAIK",
        })
        # Fu = 0.88; T = 10M * 1.0 * 0.88 * 1.0 = 8,800,000; Pmax = 8.8M * 0.6 = 5,280,000
        self.assertEqual(res1["nilai_taksiran"], Decimal("8800000"))
        self.assertEqual(res1["maks_pinjaman"], Decimal("5280000"))

        res2 = self.app.hitung_taksiran("LAPTOP", {
            "harga_pasar": 20000000,
            "spesifikasi": "HIGH",
            "umur": 2,
            "kondisi": "CUKUP",
        })
        # Fs=1.2; Fu = 1 - 0.24 = 0.76; Fk=0.8; T = 20M * 1.2 * 0.76 * 0.8 = 14,592,000
        # Pmax = 14,592,000 * 0.60 = 8,755,200
        self.assertEqual(res2["nilai_taksiran"], Decimal("14592000"))
        self.assertEqual(res2["maks_pinjaman"], Decimal("8755200"))

    def test_formula_lainnya(self):
        # Formula: T = Hp * Fk; LTV = 0.50
        # Kondisi BAIK (Fk = 1.0)
        res1 = self.app.hitung_taksiran("LAINNYA", {
            "harga_pasar": 2000000,
            "kondisi": "BAIK",
        })
        self.assertEqual(res1["nilai_taksiran"], Decimal("2000000"))
        self.assertEqual(res1["persen"], Decimal("0.50"))
        self.assertEqual(res1["maks_pinjaman"], Decimal("1000000"))

        # Kondisi CUKUP (Fk = 0.8)
        res2 = self.app.hitung_taksiran("LAINNYA", {
            "harga_pasar": 3000000,
            "kondisi": "CUKUP",
        })
        self.assertEqual(res2["nilai_taksiran"], Decimal("2400000"))
        self.assertEqual(res2["maks_pinjaman"], Decimal("1200000"))

        # Kondisi BURUK (Fk = 0.6)
        res3 = self.app.hitung_taksiran("LAINNYA", {
            "harga_pasar": 1000000,
            "kondisi": "BURUK",
        })
        self.assertEqual(res3["nilai_taksiran"], Decimal("600000"))
        self.assertEqual(res3["maks_pinjaman"], Decimal("300000"))

    def test_invalid_appraisal_inputs(self):
        with self.assertRaises(ValidasiError):
            self.app.hitung_taksiran("INVALID_TYPE", {})

        with self.assertRaises(ValidasiError):
            self.app.hitung_taksiran("EMAS", {"berat": -5, "kadar": 24})

        with self.assertRaises(ValidasiError):
            self.app.hitung_taksiran("EMAS", {"berat": 10, "kadar": 30})  # > 24 karat

        with self.assertRaises(ValidasiError):
            self.app.hitung_taksiran("LAINNYA", {"harga_pasar": 0, "kondisi": "BAIK"})


if __name__ == "__main__":
    unittest.main()
