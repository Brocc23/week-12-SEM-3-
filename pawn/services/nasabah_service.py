"""Layanan Pengelolaan Nasabah dan Riwayat Finansial Agunan."""
from datetime import date
from decimal import Decimal
from pawn.errors import AturanBisnisError, DataTidakDitemukanError, ValidasiError
from pawn.repository.repos import CabangRepo, NasabahRepo, PinjamanRepo, TransaksiRepo


class NasabahService:
    """Mengelola siklus hidup data nasabah dan riwayat peminjaman."""

    def __init__(
        self,
        nasabah_repo: NasabahRepo,
        cabang_repo: CabangRepo,
        pinjaman_repo: PinjamanRepo,
        transaksi_repo: TransaksiRepo,
    ):
        self.nasabah_repo = nasabah_repo
        self.cabang_repo = cabang_repo
        self.pinjaman_repo = pinjaman_repo
        self.transaksi_repo = transaksi_repo

    def tambah_nasabah(
        self,
        cabang_id: int,
        nik: str,
        nama: str,
        alamat: str,
        telepon: str,
        email: str,
        tgl_daftar: date | str,
    ) -> dict:
        """Mendaftarkan nasabah baru dengan kode urut unik per cabang."""
        nik = (nik or "").strip()
        nama = (nama or "").strip()
        alamat = (alamat or "").strip()
        telepon = (telepon or "").strip()
        email = (email or "").strip()

        if not nik or len(nik) < 8:
            raise ValidasiError("NIK wajib diisi dengan format yang valid (minimal 8 digit)")
        if not nama:
            raise ValidasiError("Nama nasabah tidak boleh kosong")
        if not alamat:
            raise ValidasiError("Alamat nasabah tidak boleh kosong")
        if not telepon:
            raise ValidasiError("Nomor telepon tidak boleh kosong")

        cabang = self.cabang_repo.get(cabang_id)
        if not cabang:
            raise DataTidakDitemukanError(f"Cabang dengan ID {cabang_id} tidak ditemukan")

        existing_nik = self.nasabah_repo.get_by_nik(nik)
        if existing_nik:
            raise ValidasiError(f"Nasabah dengan NIK '{nik}' sudah terdaftar dalam sistem")

        seq = self.nasabah_repo.next_seq("nasabah")
        kode = f"NSB-{seq:04d}"

        nasabah_id = self.nasabah_repo.insert({
            "cabang_id": cabang_id,
            "kode": kode,
            "nik": nik,
            "nama": nama,
            "alamat": alamat,
            "telepon": telepon,
            "email": email,
            "tgl_daftar": str(tgl_daftar),
            "status": "AKTIF",
        })

        return self.nasabah_repo.get(nasabah_id)

    def daftar_nasabah(self, cari: str = "", cabang_id: int | None = None) -> list[dict]:
        """Pencarian nasabah berdasarkan nama, NIK, kode, atau nomor telepon."""
        cari = (cari or "").strip()
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("n.cabang_id = ?")
            params.append(cabang_id)

        if cari:
            clauses.append("(n.nama LIKE ? OR n.nik LIKE ? OR n.kode LIKE ? OR n.telepon LIKE ?)")
            pattern = f"%{cari}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT n.*, c.nama as nama_cabang, c.kode as kode_cabang
            FROM nasabah n
            JOIN cabang c ON n.cabang_id = c.id
            {where_sql}
            ORDER BY n.id DESC
        """
        return self.nasabah_repo.query(sql, tuple(params))

    def ubah_status_nasabah(self, nasabah_id: int, status: str) -> None:
        """Mengubah status operasional nasabah (AKTIF / DITANGGUHKAN)."""
        nasabah = self.nasabah_repo.get(nasabah_id)
        if not nasabah:
            raise DataTidakDitemukanError(f"Nasabah dengan ID {nasabah_id} tidak ditemukan")

        status_clean = (status or "").upper().strip()
        if status_clean not in ("AKTIF", "DITANGGUHKAN"):
            raise ValidasiError(f"Status tidak valid: {status}. Harus AKTIF atau DITANGGUHKAN")

        self.nasabah_repo.update(nasabah_id, {"status": status_clean})

    def hapus_nasabah(self, nasabah_id: int) -> None:
        """Menghapus data nasabah yang tidak memiliki tanggungan pinjaman aktif."""
        nasabah = self.nasabah_repo.get(nasabah_id)
        if not nasabah:
            raise DataTidakDitemukanError(f"Nasabah dengan ID {nasabah_id} tidak ditemukan")

        pinjaman_aktif = self.pinjaman_repo.find(nasabah_id=nasabah_id)
        for p in pinjaman_aktif:
            if p["status"] in ("AKTIF", "JATUH_TEMPO", "DALAM_PROSES_LELANG"):
                raise AturanBisnisError(
                    f"Tidak dapat menghapus nasabah. Kontrak pinjaman '{p['no_kontrak']}' masih berjalan."
                )

        if pinjaman_aktif:  # riwayat kontrak harus tetap utuh (integritas referensial)
            raise AturanBisnisError("Nasabah memiliki riwayat pinjaman dan tidak dapat dihapus; gunakan status DITANGGUHKAN")
        self.nasabah_repo.delete(nasabah_id)

    def riwayat_nasabah(self, nasabah_id: int) -> dict:
        """Menghasilkan rekapitulasi riwayat seluruh kontrak dan transaksi nasabah."""
        nasabah = self.nasabah_repo.get(nasabah_id)
        if not nasabah:
            raise DataTidakDitemukanError(f"Nasabah dengan ID {nasabah_id} tidak ditemukan")

        daftar_pinjaman = self.pinjaman_repo.find(nasabah_id=nasabah_id)
        hasil_pinjaman = []
        for p in daftar_pinjaman:
            row = dict(p)
            for m in ("nilai_taksiran", "pokok", "sisa_pokok", "bunga_terutang", "biaya_admin_terutang", "denda_terutang"):
                row[m] = Decimal(str(row[m]))
            hasil_pinjaman.append(row)

        pinjaman_ids = [p["id"] for p in daftar_pinjaman]
        riwayat_trx = []
        if pinjaman_ids:
            placeholders = ", ".join(["?"] * len(pinjaman_ids))
            trx_rows = self.transaksi_repo.query(
                f"SELECT * FROM transaksi WHERE pinjaman_id IN ({placeholders}) ORDER BY id DESC",
                tuple(pinjaman_ids),
            )
            for t in trx_rows:
                t_dict = dict(t)
                t_dict["jumlah"] = Decimal(str(t_dict["jumlah"]))
                riwayat_trx.append(t_dict)

        return {
            "nasabah": dict(nasabah),
            "pinjaman": hasil_pinjaman,
            "transaksi": riwayat_trx,
        }

    def nasabah_menunggak(self, cabang_id: int | None = None, hari_ini: date = None) -> list[dict]:
        """Daftar nasabah yang memiliki pinjaman berstatus JATUH_TEMPO atau telah lewat tenggat."""
        today_str = str(hari_ini or date.today())
        clauses = ["(p.status = 'JATUH_TEMPO' OR (p.status = 'AKTIF' AND p.tgl_jatuh_tempo < ?))"]
        params = [today_str]

        if cabang_id is not None:
            clauses.append("p.cabang_id = ?")
            params.append(cabang_id)

        where_sql = "WHERE " + " AND ".join(clauses)
        sql = f"""
            SELECT p.id as pinjaman_id, p.no_kontrak, p.sisa_pokok, p.bunga_terutang,
                   p.denda_terutang, p.tgl_jatuh_tempo, p.status as status_pinjaman,
                   n.id as nasabah_id, n.kode as kode_nasabah, n.nama as nama_nasabah,
                   n.telepon, n.email, c.nama as nama_cabang
            FROM pinjaman p
            JOIN nasabah n ON p.nasabah_id = n.id
            JOIN cabang c ON p.cabang_id = c.id
            {where_sql}
            ORDER BY p.tgl_jatuh_tempo ASC
        """
        rows = self.pinjaman_repo.query(sql, tuple(params))
        hasil = []
        for r in rows:
            d = dict(r)
            d["sisa_pokok"] = Decimal(str(d["sisa_pokok"]))
            d["bunga_terutang"] = Decimal(str(d["bunga_terutang"]))
            d["denda_terutang"] = Decimal(str(d["denda_terutang"]))
            d["total_tunggakan"] = d["sisa_pokok"] + d["bunga_terutang"] + d["denda_terutang"]
            hasil.append(d)
        return hasil
