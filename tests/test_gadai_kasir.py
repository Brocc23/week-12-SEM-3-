"""Tests for Pawn Loans (Gadai), Cashier Waterfall, Extensions, and Repayments."""

from decimal import Decimal
from datetime import date, timedelta
import unittest
from pawn.errors import AturanBisnisError, ValidasiError
from tests.base import BaseTestCase


class TestGadaiKasir(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.login("admin", "admin123")
        self.nasabah = self.app.daftar_nasabah()[0]

    def test_ajukan_gadai_success(self):
        res = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Cincin Emas Murni 10gr",
            atribut={"berat": 10, "kadar": 24},
            jumlah_pinjaman=5000000,
        )
        self.assertTrue(res["no_kontrak"].startswith("GDI-"))
        self.assertEqual(res["pokok"], Decimal("5000000"))
        self.assertEqual(res["status"], "AKTIF")
        # Biaya admin default 1% = 50,000
        self.assertEqual(res["biaya_admin_terutang"], Decimal("50000"))

    def test_ajukan_gadai_lainnya_end_to_end(self):
        # LAINNYA with Hp=2,000,000, BAIK -> T=2,000,000, LTV=0.50, Pmax=1,000,000
        res = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="LAINNYA",
            deskripsi="Kamera Mirrorless Klasik",
            atribut={"harga_pasar": 2000000, "kondisi": "BAIK"},
            jumlah_pinjaman=800000,
        )
        self.assertTrue(res["no_kontrak"].startswith("GDI-"))
        self.assertEqual(res["pokok"], Decimal("800000"))
        self.assertEqual(res["persen_pinjaman"], Decimal("0.50"))
        self.assertEqual(res["status"], "AKTIF")
        self.assertEqual(res["jenis_barang"], "LAINNYA")
        # Biaya admin default 1% of 800,000 = 8,000
        self.assertEqual(res["biaya_admin_terutang"], Decimal("8000"))

    def test_loan_exceeding_pmax_rejected(self):
        # Emas 10gr 24K: T = 10,000,000; Pmax = 9,000,000
        with self.assertRaises(AturanBisnisError):
            self.app.ajukan_gadai(
                nasabah_id=self.nasabah["id"],
                jenis="EMAS",
                deskripsi="Cincin Emas Murni 10gr",
                atribut={"berat": 10, "kadar": 24},
                jumlah_pinjaman=9500000,  # Exceeds Pmax
            )

    def test_loan_lainnya_exceeding_pmax_rejected(self):
        # LAINNYA with Hp=2,000,000, BAIK -> T=2,000,000, Pmax=1,000,000
        with self.assertRaises(AturanBisnisError):
            self.app.ajukan_gadai(
                nasabah_id=self.nasabah["id"],
                jenis="LAINNYA",
                deskripsi="Kamera Mirrorless Klasik",
                atribut={"harga_pasar": 2000000, "kondisi": "BAIK"},
                jumlah_pinjaman=1200000,  # Exceeds Pmax of 1,000,000
            )

    def test_duplicate_pledge_rejected(self):
        """Pledging identical collateral that is already active/pledged should be rejected."""
        self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Kalung Emas Seri 12345",
            atribut={"berat": 10, "kadar": 24, "no_seri": "12345"},
            jumlah_pinjaman=4000000,
        )
        # Attempting to pledge the exact same active collateral again
        with self.assertRaises((AturanBisnisError, ValidasiError)):
            self.app.ajukan_gadai(
                nasabah_id=self.nasabah["id"],
                jenis="EMAS",
                deskripsi="Kalung Emas Seri 12345",
                atribut={"berat": 10, "kadar": 24, "no_seri": "12345"},
                jumlah_pinjaman=4000000,
            )

    def test_payment_zero_or_negative_rejected(self):
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Gelang Emas",
            atribut={"berat": 5, "kadar": 24},
            jumlah_pinjaman=2000000,
        )
        with self.assertRaises((ValidasiError, ValueError)):
            self.app.bayar_angsuran(loan["no_kontrak"], 0, "TUNAI")

        with self.assertRaises((ValidasiError, ValueError)):
            self.app.bayar_angsuran(loan["no_kontrak"], -100000, "TUNAI")

    def test_failed_payment_leaves_balance_unchanged(self):
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Kalung Emas",
            atribut={"berat": 10, "kadar": 24},
            jumlah_pinjaman=5000000,
        )
        kewajiban_sebelum = self.app.hitung_kewajiban(loan["no_kontrak"])

        # QRIS has hard limit of 10,000,000; attempting payment with unsupported or violating params
        try:
            self.app.bayar_angsuran(loan["no_kontrak"], Decimal("50000000"), "QRIS")
        except Exception:
            pass

        kewajiban_sesudah = self.app.hitung_kewajiban(loan["no_kontrak"])
        self.assertEqual(kewajiban_sebelum["sisa_pokok"], kewajiban_sesudah["sisa_pokok"])
        self.assertEqual(kewajiban_sebelum["biaya_admin"], kewajiban_sesudah["biaya_admin"])
        self.assertEqual(kewajiban_sebelum["total"], kewajiban_sesudah["total"])

    def test_waterfall_allocation_order(self):
        """
        Waterfall order:
        1. Biaya Admin
        2. Denda Keterlambatan
        3. Bunga Terutang
        4. Sisa Pokok Pinjaman
        """
        today = date.today()
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Anting Emas",
            atribut={"berat": 10, "kadar": 24},
            jumlah_pinjaman=5000000,
        )
        # Biaya admin = 50,000
        # Fast forward simulation date to accumulate bunga (e.g., 20 days -> 2 periods @ 1.2% = 120,000)
        tgl_sim = today + timedelta(days=20)
        self.app.set_tanggal_simulasi(tgl_sim)
        kewajiban = self.app.hitung_kewajiban(loan["no_kontrak"])
        self.assertEqual(kewajiban["biaya_admin"], Decimal("50000"))
        self.assertEqual(kewajiban["bunga"], Decimal("120000"))

        # Pay partial amount of 100,000
        # Waterfall: 50,000 covers admin -> 50,000 covers bunga -> 0 for pokok
        res = self.app.bayar_angsuran(loan["no_kontrak"], 100000, "TUNAI")
        self.assertEqual(res["alokasi"]["bayar_admin"], Decimal("50000"))
        self.assertEqual(res["alokasi"]["bayar_denda"], Decimal("0"))
        self.assertEqual(res["alokasi"]["bayar_bunga"], Decimal("50000"))
        self.assertEqual(res["alokasi"]["bayar_pokok"], Decimal("0"))

        # Check remaining
        det = self.app.detail_pinjaman(loan["no_kontrak"])
        self.assertEqual(det["biaya_admin_terutang"], Decimal("0"))
        self.assertEqual(det["bunga_terutang"], Decimal("70000"))
        self.assertEqual(det["sisa_pokok"], Decimal("5000000"))

    def test_pelunasan_insufficient_rejected(self):
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Cincin Emas",
            atribut={"berat": 5, "kadar": 24},
            jumlah_pinjaman=2000000,
        )
        kew = self.app.hitung_kewajiban(loan["no_kontrak"])
        total = kew["total"]

        # Paying 1 rupiah less must be rejected
        with self.assertRaises(AturanBisnisError):
            self.app.lunasi(loan["no_kontrak"], total - Decimal("1000"), "TUNAI")

        det = self.app.detail_pinjaman(loan["no_kontrak"])
        self.assertEqual(det["status"], "AKTIF")

    def test_pelunasan_exact_amount_succeeds(self):
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Cincin Emas",
            atribut={"berat": 5, "kadar": 24},
            jumlah_pinjaman=2000000,
        )
        kew = self.app.hitung_kewajiban(loan["no_kontrak"])
        total = kew["total"]

        res = self.app.lunasi(loan["no_kontrak"], total, "TUNAI")
        self.assertEqual(res["status"], "BERHASIL")

        det = self.app.detail_pinjaman(loan["no_kontrak"])
        self.assertEqual(det["status"], "LUNAS")
        self.assertEqual(det["sisa_pokok"], Decimal("0"))

    def test_perpanjangan_bunga_denda_unpaid_rejected(self):
        today = date.today()
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Liontin Emas",
            atribut={"berat": 5, "kadar": 24},
            jumlah_pinjaman=2000000,
        )
        # Advance 20 days so interest accrues
        self.app.set_tanggal_simulasi(today + timedelta(days=20))
        # Extension must be rejected because bunga > 0
        with self.assertRaises(AturanBisnisError):
            self.app.perpanjang(loan["no_kontrak"], "TUNAI")

    def test_perpanjangan_max_limit_enforced(self):
        loan = self.app.ajukan_gadai(
            nasabah_id=self.nasabah["id"],
            jenis="EMAS",
            deskripsi="Liontin Emas",
            atribut={"berat": 5, "kadar": 24},
            jumlah_pinjaman=2000000,
        )
        # Settle interest and admin so extension can proceed
        kew = self.app.hitung_kewajiban(loan["no_kontrak"])
        self.app.bayar_angsuran(loan["no_kontrak"], kew["biaya_admin"] + kew["bunga"], "TUNAI")

        # 1st Extension
        res1 = self.app.perpanjang(loan["no_kontrak"], "TUNAI")
        self.assertIsNotNone(res1["id"])

        # 2nd Extension
        res2 = self.app.perpanjang(loan["no_kontrak"], "TUNAI")
        self.assertIsNotNone(res2["id"])

        # 3rd Extension must be rejected (max limit = 2)
        with self.assertRaises(AturanBisnisError):
            self.app.perpanjang(loan["no_kontrak"], "TUNAI")


if __name__ == "__main__":
    unittest.main()
