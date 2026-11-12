"""Layanan Pelaporan Finansial dan Rekapitulasi Aset Agunan."""
from datetime import date
from decimal import Decimal
from pawn.export import export_csv
from pawn.models.laporan import LaporanAsetJaminan, LaporanLabaRugi
from pawn.repository.repos import BarangRepo, JurnalRepo, LelangRepo, PerpanjanganRepo, TransaksiRepo


class LaporanService:
    """Menghasilkan laporan laba rugi berkala dan inventaris aset agunan sistem."""

    def __init__(
        self,
        jurnal_repo: JurnalRepo,
        transaksi_repo: TransaksiRepo,
        lelang_repo: LelangRepo,
        perpanjangan_repo: PerpanjanganRepo,
        barang_repo: BarangRepo,
    ):
        self.jurnal_repo = jurnal_repo
        self.transaksi_repo = transaksi_repo
        self.lelang_repo = lelang_repo
        self.perpanjangan_repo = perpanjangan_repo
        self.barang_repo = barang_repo

    def laporan_laba_rugi(
        self,
        dari: date | str,
        sampai: date | str,
        cabang_id: int | None = None,
    ) -> dict:
        """
        Menghasilkan laporan laba rugi operasional dari buku jurnal akuntansi:
        - Pendapatan Bunga
        - Pendapatan Administrasi
        - Pendapatan Denda
        - Pendapatan Biaya Perpanjangan
        - Beban Kerugian Lelang
        - Laba Bersih
        """
        dari_str = str(dari)
        sampai_str = str(sampai)

        sql_jurnal = """
            SELECT j.*
            FROM jurnal j
            WHERE DATE(j.waktu) >= ? AND DATE(j.waktu) <= ?
            ORDER BY j.id ASC
        """
        jurnal_rows = self.jurnal_repo.query(sql_jurnal, (dari_str, sampai_str))

        pendapatan_bunga = Decimal("0")
        pendapatan_admin = Decimal("0")
        pendapatan_denda = Decimal("0")
        biaya_perpanjangan = Decimal("0")
        kerugian_lelang = Decimal("0")

        rows = []
        for r in jurnal_rows:
            d = dict(r)
            debit = Decimal(str(d["debit"]))
            kredit = Decimal(str(d["kredit"]))
            akun = d["akun"]

            d["debit"] = debit
            d["kredit"] = kredit
            rows.append(d)

            if "Bunga" in akun:
                pendapatan_bunga += kredit
            elif "Administrasi" in akun or "Admin" in akun:
                pendapatan_admin += kredit
            elif "Denda" in akun:
                pendapatan_denda += kredit
            elif "Perpanjangan" in akun:
                biaya_perpanjangan += kredit
            elif "Kerugian Lelang" in akun:
                kerugian_lelang += debit

        # Fallback jika jurnal belum mencakup (misal data hasil seed tanpa jurnal penuh)
        if pendapatan_bunga == Decimal("0") and pendapatan_admin == Decimal("0") and biaya_perpanjangan == Decimal("0"):
            sql_trx = """
                SELECT t.*
                FROM transaksi t
                JOIN pinjaman p ON t.pinjaman_id = p.id
                WHERE t.status = 'BERHASIL'
                  AND DATE(t.waktu) >= ? AND DATE(t.waktu) <= ?
            """
            params_trx = [dari_str, sampai_str]
            if cabang_id is not None:
                sql_trx += " AND p.cabang_id = ?"
                params_trx.append(cabang_id)

            t_rows = self.transaksi_repo.query(sql_trx, tuple(params_trx))
            for t in t_rows:
                j = t["jenis"]
                nom = Decimal(str(t["jumlah"]))
                if j == "PERPANJANGAN":
                    biaya_perpanjangan += nom

            sql_lelang = """
                SELECT l.*
                FROM lelang l
                JOIN pinjaman p ON l.pinjaman_id = p.id
                WHERE DATE(l.tanggal) >= ? AND DATE(l.tanggal) <= ?
            """
            params_lelang = [dari_str, sampai_str]
            if cabang_id is not None:
                sql_lelang += " AND p.cabang_id = ?"
                params_lelang.append(cabang_id)

            l_rows = self.lelang_repo.query(sql_lelang, tuple(params_lelang))
            for l in l_rows:
                kerugian_lelang += Decimal(str(l["kerugian"]))

        model = LaporanLabaRugi(
            pendapatan_bunga=pendapatan_bunga,
            pendapatan_admin=pendapatan_admin,
            denda=pendapatan_denda,
            biaya_perpanjangan=biaya_perpanjangan,
            kerugian_lelang=kerugian_lelang,
            rows=rows,
        )
        return model.hasilkan()

    def laporan_aset_jaminan(self, cabang_id: int | None = None) -> list[dict]:
        """Menghasilkan rekapitulasi seluruh agunan fisik beserta nilai taksiran dan statusnya."""
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("n.cabang_id = ?")
            params.append(cabang_id)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT b.id, b.kode as kode_barang, b.jenis, b.deskripsi, b.nilai_taksiran,
                   b.status, n.nama as nama_nasabah, n.nik, c.nama as nama_cabang,
                   p.no_kontrak, p.sisa_pokok, p.status as status_pinjaman
            FROM barang_jaminan b
            JOIN nasabah n ON b.nasabah_id = n.id
            JOIN cabang c ON n.cabang_id = c.id
            LEFT JOIN pinjaman p ON p.barang_id = b.id
            {where_sql}
            ORDER BY b.id DESC
        """
        rows = self.barang_repo.query(sql, tuple(params))
        hasil = []
        for r in rows:
            d = dict(r)
            d["nilai_taksiran"] = Decimal(str(d["nilai_taksiran"]))
            if d.get("sisa_pokok") is not None:
                d["sisa_pokok"] = Decimal(str(d["sisa_pokok"]))
            hasil.append(d)

        model = LaporanAsetJaminan(hasil)
        return model.hasilkan()

    def export_laporan_csv(self, rows: list[dict], path: str) -> None:
        """Mengekspor struktur baris laporan ke file berkas CSV."""
        export_csv(rows, path)
