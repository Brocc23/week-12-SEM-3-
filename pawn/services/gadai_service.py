"""Layanan Operasional Gadai, Kasir Waterfall, Gudang, dan Lelang Agunan."""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from pawn.errors import AturanBisnisError, DataTidakDitemukanError, ValidasiError
from pawn.models.barang import buat_barang
from pawn.models.metode_pembayaran import dapatkan_metode_pembayaran
from pawn.models.pinjaman import Pinjaman
from pawn.repository.repos import (
    BarangRepo,
    CabangRepo,
    GudangRepo,
    JurnalRepo,
    LelangRepo,
    NasabahRepo,
    NotifikasiRepo,
    ParameterRepo,
    PenggunaRepo,
    PerpanjanganRepo,
    PinjamanRepo,
    TransaksiRepo,
)
from pawn.services.penaksiran_service import PenaksiranService


class GadaiService:
    """Mengelola alur bisnis gadai dari pengajuan hingga pelunasan atau lelang."""

    def __init__(
        self,
        pinjaman_repo: PinjamanRepo,
        barang_repo: BarangRepo,
        nasabah_repo: NasabahRepo,
        cabang_repo: CabangRepo,
        pengguna_repo: PenggunaRepo,
        transaksi_repo: TransaksiRepo,
        perpanjangan_repo: PerpanjanganRepo,
        gudang_repo: GudangRepo,
        notifikasi_repo: NotifikasiRepo,
        lelang_repo: LelangRepo,
        parameter_repo: ParameterRepo,
        jurnal_repo: JurnalRepo,
        penaksiran_service: PenaksiranService,
    ):
        self.pinjaman_repo = pinjaman_repo
        self.barang_repo = barang_repo
        self.nasabah_repo = nasabah_repo
        self.cabang_repo = cabang_repo
        self.pengguna_repo = pengguna_repo
        self.transaksi_repo = transaksi_repo
        self.perpanjangan_repo = perpanjangan_repo
        self.gudang_repo = gudang_repo
        self.notifikasi_repo = notifikasi_repo
        self.lelang_repo = lelang_repo
        self.parameter_repo = parameter_repo
        self.jurnal_repo = jurnal_repo
        self.penaksiran_service = penaksiran_service

    def _format_pinjaman_row(self, row: dict) -> dict:
        """Helper untuk konversi kolom uang TEXT ke Decimal."""
        d = dict(row)
        for col in ("nilai_taksiran", "pokok", "sisa_pokok", "bunga_terutang", "biaya_admin_terutang", "denda_terutang"):
            if col in d and d[col] is not None:
                d[col] = Decimal(str(d[col]))
        if "persen_pinjaman" in d and d["persen_pinjaman"] is not None:
            d["persen_pinjaman"] = Decimal(str(d["persen_pinjaman"]))
        if "suku_bunga_periode" in d and d["suku_bunga_periode"] is not None:
            d["suku_bunga_periode"] = Decimal(str(d["suku_bunga_periode"]))
        return d

    def _sinkronkan_pinjaman_obj(self, row: dict, hari_ini: date) -> Pinjaman:
        """Membuat instance Pinjaman dan menyinkronkan bunga serta denda hari berjalan."""
        clean = self._format_pinjaman_row(row)
        pinjaman = Pinjaman(
            id=clean["id"],
            no_kontrak=clean["no_kontrak"],
            cabang_id=clean["cabang_id"],
            nasabah_id=clean["nasabah_id"],
            barang_id=clean["barang_id"],
            petugas_id=clean["petugas_id"],
            penaksir_id=clean["penaksir_id"],
            nilai_taksiran=clean["nilai_taksiran"],
            persen_pinjaman=clean["persen_pinjaman"],
            pokok=clean["pokok"],
            sisa_pokok=clean["sisa_pokok"],
            bunga_terutang=clean["bunga_terutang"],
            biaya_admin_terutang=clean["biaya_admin_terutang"],
            denda_terutang=clean["denda_terutang"],
            suku_bunga_periode=clean["suku_bunga_periode"],
            tgl_transaksi=clean["tgl_transaksi"],
            tgl_jatuh_tempo=clean["tgl_jatuh_tempo"],
            jumlah_perpanjangan=clean["jumlah_perpanjangan"],
            status=clean["status"],
        )

        sql_paid = """
            SELECT 
                COALESCE(SUM(CASE WHEN akun LIKE '%Bunga%' THEN kredit ELSE 0 END), 0) as bunga_dibayar,
                COALESCE(SUM(CASE WHEN akun LIKE '%Denda%' THEN kredit ELSE 0 END), 0) as denda_dibayar
            FROM jurnal
            WHERE no_ref = ?
        """
        paid_rows = self.jurnal_repo.query(sql_paid, (clean["no_kontrak"],))
        bunga_dibayar = Decimal(str(paid_rows[0]["bunga_dibayar"])) if paid_rows else Decimal("0")
        denda_dibayar = Decimal(str(paid_rows[0]["denda_dibayar"])) if paid_rows else Decimal("0")

        denda_per_hari = Decimal(str(self.parameter_repo.get_value("denda_per_hari", "0.002")))
        pinjaman.sinkronkan_bunga_dan_denda(hari_ini, denda_per_hari, bunga_dibayar, denda_dibayar)
        return pinjaman

    def ajukan_gadai(
        self,
        nasabah_id: int,
        jenis: str,
        deskripsi: str,
        atribut: dict,
        jumlah_pinjaman: Decimal | str | int,
        tenor_hari: int | None = None,
        lokasi_gudang: str = "",
        kondisi_barang: str = "",
        penaksir_id: int | None = None,
        petugas_id: int | None = None,
        cabang_id: int | None = None,
        hari_ini: date | None = None,
    ) -> dict:
        """
        Alur pengajuan gadai (9 Langkah Bisnis):
        1. Verifikasi nasabah aktif
        2. Taksir agunan
        3. Validasi limit pinjaman (<= Pmax)
        4. Pembuatan nomor kontrak unik
        5. Pencatatan barang jaminan (status TERGADAI)
        6. Pembuatan kontrak pinjaman (status AKTIF)
        7. Pencatatan transaksi pencairan
        8. Pembukuan jurnal pencairan
        9. Pencatatan penyimpanan barang di gudang
        """
        today = hari_ini or date.today()

        # Step 1: Verifikasi nasabah aktif
        nasabah = self.nasabah_repo.get(nasabah_id)
        if not nasabah:
            raise DataTidakDitemukanError(f"Nasabah dengan ID {nasabah_id} tidak ditemukan")
        if nasabah["status"] != "AKTIF":
            raise AturanBisnisError(f"Nasabah {nasabah['nama']} sedang ditangguhkan dan tidak dapat mengajukan pinjaman")

        target_cabang_id = cabang_id or nasabah["cabang_id"]
        cabang = self.cabang_repo.get(target_cabang_id)
        if not cabang:
            raise DataTidakDitemukanError(f"Cabang dengan ID {target_cabang_id} tidak ditemukan")

        # Step 2: Penaksiran
        if not penaksir_id:
            penaksir_list = self.pengguna_repo.find(cabang_id=target_cabang_id, role="PENAKSIR", aktif=1)
            if not penaksir_list:
                penaksir_list = self.pengguna_repo.find(role="PENAKSIR", aktif=1)
            penaksir_id = penaksir_list[0]["id"] if penaksir_list else (petugas_id or 1)

        taksiran = self.penaksiran_service.hitung_taksiran(jenis, atribut)
        nilai_taksiran = taksiran["nilai_taksiran"]
        persen_ltv = taksiran["persen"]
        p_max = taksiran["maks_pinjaman"]

        # Step 3: Validasi jumlah pinjaman <= Pmax
        nominal = Decimal(str(jumlah_pinjaman)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if nominal <= Decimal("0"):
            raise ValidasiError("Jumlah pinjaman harus lebih dari 0")
        if nominal > p_max:
            raise AturanBisnisError(
                f"Jumlah pinjaman Rp {nominal:,} melebihi batas maksimal taksiran Rp {p_max:,}"
            )

        # shortcut: identitas barang = jenis+deskripsi (tanpa nomor seri), upgrade bila ada kolom serial
        kunci = (jenis.upper(), deskripsi.strip().lower())
        for b in self.barang_repo.query(
            "SELECT jenis, deskripsi FROM barang_jaminan WHERE status IN ('TERGADAI','JATUH_TEMPO','DALAM_PROSES_LELANG')"
        ):
            if (b["jenis"], b["deskripsi"].strip().lower()) == kunci:
                raise AturanBisnisError("Barang ini masih menjadi jaminan pada kontrak gadai yang aktif")

        # Step 4: Nomor kontrak unik: GDI-<kodecabang>-<yyyymmdd>-<seq4>
        cabang_kode = cabang["kode"].upper()
        date_str = today.strftime("%Y%m%d")
        seq_kontrak = self.pinjaman_repo.next_seq(f"kontrak_{cabang_kode}_{date_str}")
        no_kontrak = f"GDI-{cabang_kode}-{date_str}-{seq_kontrak:04d}"

        # Step 5: Barang jaminan record
        seq_brg = self.barang_repo.next_seq("barang")
        kode_barang = f"BRG-{seq_brg:04d}"
        barang_id = self.barang_repo.insert({
            "kode": kode_barang,
            "nasabah_id": nasabah_id,
            "jenis": jenis.upper(),
            "deskripsi": deskripsi,
            "atribut": json.dumps(atribut),
            "nilai_taksiran": nilai_taksiran,
            "status": "TERGADAI",
            "penaksir_id": penaksir_id,
        })

        # Step 6: Pembuatan pinjaman record
        tenor = tenor_hari or int(self.parameter_repo.get_value("tenor_hari_default", 120))
        tgl_jatuh_tempo = today + timedelta(days=tenor)

        biaya_admin_persen = Decimal(str(self.parameter_repo.get_value("biaya_admin_persen", "0.01")))
        biaya_admin_awal = (nominal * biaya_admin_persen).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        bunga_per_periode = Decimal(str(self.parameter_repo.get_value("bunga_per_periode", "0.012")))

        pinjaman_id = self.pinjaman_repo.insert({
            "no_kontrak": no_kontrak,
            "cabang_id": target_cabang_id,
            "nasabah_id": nasabah_id,
            "barang_id": barang_id,
            "petugas_id": petugas_id or 1,
            "penaksir_id": penaksir_id,
            "nilai_taksiran": nilai_taksiran,
            "persen_pinjaman": persen_ltv,
            "pokok": nominal,
            "sisa_pokok": nominal,
            "bunga_terutang": Decimal("0"),
            "biaya_admin_terutang": biaya_admin_awal,
            "denda_terutang": Decimal("0"),
            "suku_bunga_periode": bunga_per_periode,
            "tgl_transaksi": str(today),
            "tgl_jatuh_tempo": str(tgl_jatuh_tempo),
            "jumlah_perpanjangan": 0,
            "status": "AKTIF",
        })

        # Step 7: Transaksi pencairan
        time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        seq_trx = self.transaksi_repo.next_seq("trx")
        no_trx = f"TRX-{time_str}-{seq_trx:04d}"
        self.transaksi_repo.insert({
            "no_transaksi": no_trx,
            "pinjaman_id": pinjaman_id,
            "jenis": "GADAI",
            "jumlah": nominal,
            "metode": "TUNAI",
            "status": "BERHASIL",
            "waktu": datetime.now().isoformat(),
            "petugas_id": petugas_id or 1,
            "keterangan": f"Pencairan dana pinjaman gadai kontrak {no_kontrak}",
        })

        # Step 8: Jurnal pencairan
        waktu_iso = datetime.now().isoformat()
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": "Piutang Pinjaman Gadai",
            "debit": nominal,
            "kredit": Decimal("0"),
            "keterangan": f"Pencairan pinjaman {no_kontrak}",
        })
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": "Kas Operasional",
            "debit": Decimal("0"),
            "kredit": nominal,
            "keterangan": f"Pengeluaran kas pencairan pinjaman {no_kontrak}",
        })

        # Step 9: Pencatatan di Gudang
        self.gudang_repo.insert({
            "kode_barang": kode_barang,
            "barang_id": barang_id,
            "pinjaman_id": pinjaman_id,
            "lokasi": lokasi_gudang or "Khasanah Utama Cabang",
            "tgl_masuk": str(today),
            "kondisi": kondisi_barang or "BAIK",
            "petugas_id": petugas_id or 1,
            "status": "TERGADAI",
        })

        return self.detail_pinjaman(no_kontrak, hari_ini=today)

    def hitung_kewajiban(self, no_kontrak: str, hari_ini: date | None = None) -> dict:
        """
        Menghitung rincian total kewajiban saat ini:
        pokok, bunga, biaya_admin, denda, total, sisa_pokok.
        """
        today = hari_ini or date.today()
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman dengan nomor kontrak {no_kontrak} tidak ditemukan")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        total = pinjaman.hitung_total_kewajiban()

        return {
            "pokok": pinjaman.pokok,
            "bunga": pinjaman.bunga_terutang,
            "biaya_admin": pinjaman.biaya_admin_terutang,
            "denda": pinjaman.denda_terutang,
            "total": total,
            "sisa_pokok": pinjaman.sisa_pokok,
        }

    def detail_pinjaman(self, no_kontrak: str, hari_ini: date | None = None) -> dict:
        """Informasi lengkap kontrak pinjaman berserta kewajiban terkini dan data agunan."""
        today = hari_ini or date.today()
        sql = """
            SELECT p.*, n.nama as nama_nasabah, n.nik, n.kode as kode_nasabah,
                   b.kode as kode_barang, b.jenis as jenis_barang, b.deskripsi as deskripsi_barang,
                   b.status as status_barang, c.nama as nama_cabang, c.kode as kode_cabang
            FROM pinjaman p
            JOIN nasabah n ON p.nasabah_id = n.id
            JOIN barang_jaminan b ON p.barang_id = b.id
            JOIN cabang c ON p.cabang_id = c.id
            WHERE p.no_kontrak = ?
        """
        rows = self.pinjaman_repo.query(sql, (no_kontrak,))
        if not rows:
            raise DataTidakDitemukanError(f"Kontrak pinjaman '{no_kontrak}' tidak ditemukan")

        raw = rows[0]
        kewajiban = self.hitung_kewajiban(no_kontrak, today)
        formatted = self._format_pinjaman_row(raw)

        # Update nilai terutang terkini dari perhitungan akrual
        formatted["bunga_terutang"] = kewajiban["bunga"]
        formatted["denda_terutang"] = kewajiban["denda"]
        formatted["kewajiban"] = kewajiban
        return formatted

    def daftar_pinjaman(
        self,
        status: str | None = None,
        cari: str = "",
        nasabah_id: int | None = None,
        cabang_id: int | None = None,
    ) -> list[dict]:
        """Menampilkan daftar pinjaman dengan filter status, kata kunci, dan nasabah."""
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("p.cabang_id = ?")
            params.append(cabang_id)

        if status:
            clauses.append("p.status = ?")
            params.append(status.upper())

        if nasabah_id is not None:
            clauses.append("p.nasabah_id = ?")
            params.append(nasabah_id)

        if cari:
            clauses.append("(p.no_kontrak LIKE ? OR n.nama LIKE ? OR n.nik LIKE ? OR b.deskripsi LIKE ?)")
            pattern = f"%{cari}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT p.*, n.nama as nama_nasabah, n.nik, b.deskripsi as deskripsi_barang,
                   c.nama as nama_cabang
            FROM pinjaman p
            JOIN nasabah n ON p.nasabah_id = n.id
            JOIN barang_jaminan b ON p.barang_id = b.id
            JOIN cabang c ON p.cabang_id = c.id
            {where_sql}
            ORDER BY p.id DESC
        """
        rows = self.pinjaman_repo.query(sql, tuple(params))
        return [self._format_pinjaman_row(r) for r in rows]

    def bayar_angsuran(
        self,
        no_kontrak: str,
        jumlah: Decimal | str | int,
        metode: str,
        petugas_id: int | None = None,
        hari_ini: date | None = None,
    ) -> dict:
        """Membayar cicilan/angsuran pinjaman dengan prioritas waterfall."""
        today = hari_ini or date.today()
        nominal = Decimal(str(jumlah)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if nominal <= Decimal("0"):
            raise ValidasiError("Nominal angsuran harus lebih dari 0")

        metode_obj = dapatkan_metode_pembayaran(metode)
        metode_obj.proses(nominal)

        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        if pinjaman.status not in ("AKTIF", "JATUH_TEMPO"):
            raise AturanBisnisError(f"Pinjaman status '{pinjaman.status}' tidak dapat diangsur")

        hasil = pinjaman.terapkan_pembayaran(nominal)

        # Update ke database
        self.pinjaman_repo.update(pinjaman.id, {
            "sisa_pokok": pinjaman.sisa_pokok,
            "bunga_terutang": pinjaman.bunga_terutang,
            "biaya_admin_terutang": pinjaman.biaya_admin_terutang,
            "denda_terutang": pinjaman.denda_terutang,
            "status": pinjaman.status,
        })

        if pinjaman.status == "LUNAS":
            self.barang_repo.update(pinjaman.barang_id, {"status": "LUNAS"})

        # Catat Transaksi
        time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        seq_trx = self.transaksi_repo.next_seq("trx")
        no_trx = f"TRX-{time_str}-{seq_trx:04d}"
        trx_id = self.transaksi_repo.insert({
            "no_transaksi": no_trx,
            "pinjaman_id": pinjaman.id,
            "jenis": "ANGSURAN",
            "jumlah": nominal,
            "metode": metode_obj.kode,
            "status": "BERHASIL",
            "waktu": datetime.now().isoformat(),
            "petugas_id": petugas_id or 1,
            "keterangan": f"Angsuran kontrak {no_kontrak} (Pokok: {hasil['bayar_pokok']}, Bunga: {hasil['bayar_bunga']})",
        })

        # Pembukuan Jurnal Akuntansi
        waktu_iso = datetime.now().isoformat()
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": f"Kas/Bank ({metode_obj.kode})",
            "debit": nominal,
            "kredit": Decimal("0"),
            "keterangan": f"Penerimaan angsuran {no_kontrak}",
        })
        if hasil["bayar_pokok"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Piutang Pinjaman Gadai",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_pokok"],
                "keterangan": f"Pelunasan pokok angsuran {no_kontrak}",
            })
        if hasil["bayar_bunga"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Bunga Gadai",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_bunga"],
                "keterangan": f"Pendapatan bunga angsuran {no_kontrak}",
            })
        if hasil["bayar_admin"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Administrasi",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_admin"],
                "keterangan": f"Pendapatan admin angsuran {no_kontrak}",
            })
        if hasil["bayar_denda"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Denda Keterlambatan",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_denda"],
                "keterangan": f"Pendapatan denda angsuran {no_kontrak}",
            })

        t_row = self.transaksi_repo.get(trx_id)
        res = dict(t_row)
        res["jumlah"] = Decimal(str(res["jumlah"]))
        res["alokasi"] = hasil
        return res

    def lunasi(
        self,
        no_kontrak: str,
        jumlah: Decimal | str | int,
        metode: str,
        petugas_id: int | None = None,
        hari_ini: date | None = None,
    ) -> dict:
        """Melunasi pinjaman sekaligus; ditolak bila nominal kurang dari total kewajiban."""
        today = hari_ini or date.today()
        nominal = Decimal(str(jumlah)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        metode_obj = dapatkan_metode_pembayaran(metode)
        metode_obj.proses(nominal)

        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        if pinjaman.status not in ("AKTIF", "JATUH_TEMPO"):
            raise AturanBisnisError(f"Pinjaman status '{pinjaman.status}' tidak dapat dilunasi")

        total_kewajiban = pinjaman.hitung_total_kewajiban()
        if nominal < total_kewajiban:
            raise AturanBisnisError(
                f"Jumlah pembayaran Rp {nominal:,} kurang dari total kewajiban pelunasan Rp {total_kewajiban:,}"
            )

        hasil = pinjaman.terapkan_pembayaran(total_kewajiban)
        pinjaman.status = "LUNAS"

        self.pinjaman_repo.update(pinjaman.id, {
            "sisa_pokok": Decimal("0"),
            "bunga_terutang": Decimal("0"),
            "biaya_admin_terutang": Decimal("0"),
            "denda_terutang": Decimal("0"),
            "status": "LUNAS",
        })
        self.barang_repo.update(pinjaman.barang_id, {"status": "LUNAS"})

        time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        seq_trx = self.transaksi_repo.next_seq("trx")
        no_trx = f"TRX-{time_str}-{seq_trx:04d}"
        trx_id = self.transaksi_repo.insert({
            "no_transaksi": no_trx,
            "pinjaman_id": pinjaman.id,
            "jenis": "PELUNASAN",
            "jumlah": total_kewajiban,
            "metode": metode_obj.kode,
            "status": "BERHASIL",
            "waktu": datetime.now().isoformat(),
            "petugas_id": petugas_id or 1,
            "keterangan": f"Pelunasan pinjaman gadai {no_kontrak}",
        })

        waktu_iso = datetime.now().isoformat()
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": f"Kas/Bank ({metode_obj.kode})",
            "debit": total_kewajiban,
            "kredit": Decimal("0"),
            "keterangan": f"Penerimaan pelunasan {no_kontrak}",
        })
        if hasil["bayar_pokok"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Piutang Pinjaman Gadai",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_pokok"],
                "keterangan": f"Pelunasan pokok {no_kontrak}",
            })
        if hasil["bayar_bunga"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Bunga Gadai",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_bunga"],
                "keterangan": f"Pendapatan bunga pelunasan {no_kontrak}",
            })
        if hasil["bayar_admin"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Administrasi",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_admin"],
                "keterangan": f"Pendapatan admin pelunasan {no_kontrak}",
            })
        if hasil["bayar_denda"] > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Denda Keterlambatan",
                "debit": Decimal("0"),
                "kredit": hasil["bayar_denda"],
                "keterangan": f"Pendapatan denda pelunasan {no_kontrak}",
            })

        t_row = self.transaksi_repo.get(trx_id)
        res = dict(t_row)
        res["jumlah"] = Decimal(str(res["jumlah"]))
        res["alokasi"] = hasil
        res["kembalian"] = nominal - total_kewajiban
        return res

    def perpanjang(
        self,
        no_kontrak: str,
        metode: str,
        petugas_id: int | None = None,
        hari_ini: date | None = None,
    ) -> dict:
        """Perpanjangan tenor pinjaman (maksimal per parameter, bunga+denda wajib lunas)."""
        today = hari_ini or date.today()
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        if pinjaman.status not in ("AKTIF", "JATUH_TEMPO"):
            raise AturanBisnisError(f"Pinjaman dengan status '{pinjaman.status}' tidak dapat diperpanjang")

        maks_perpanjangan = int(self.parameter_repo.get_value("maks_perpanjangan", 2))
        if pinjaman.jumlah_perpanjangan >= maks_perpanjangan:
            raise AturanBisnisError(f"Maksimal perpanjangan ({maks_perpanjangan} kali) telah tercapai")

        if pinjaman.bunga_terutang > Decimal("0") or pinjaman.denda_terutang > Decimal("0"):
            raise AturanBisnisError("Bunga dan denda harus dilunasi terlebih dahulu sebelum perpanjangan")

        biaya_perpanjangan_persen = Decimal(str(self.parameter_repo.get_value("biaya_perpanjangan_persen", "0.01")))
        biaya = (pinjaman.sisa_pokok * biaya_perpanjangan_persen).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        metode_obj = dapatkan_metode_pembayaran(metode)
        metode_obj.proses(biaya)

        tenor_default = int(self.parameter_repo.get_value("tenor_hari_default", 120))
        tgl_lama = pinjaman.tgl_jatuh_tempo
        tgl_baru = tgl_lama + timedelta(days=tenor_default)

        pinjaman.perpanjang_jatuh_tempo(tgl_baru)
        pinjaman.status = "AKTIF"

        self.pinjaman_repo.update(pinjaman.id, {
            "tgl_jatuh_tempo": str(tgl_baru),
            "jumlah_perpanjangan": pinjaman.jumlah_perpanjangan,
            "status": "AKTIF",
        })

        perp_id = self.perpanjangan_repo.insert({
            "pinjaman_id": pinjaman.id,
            "tgl_lama": str(tgl_lama),
            "tgl_baru": str(tgl_baru),
            "biaya": biaya,
            "waktu": datetime.now().isoformat(),
            "petugas_id": petugas_id or 1,
        })

        time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        seq_trx = self.transaksi_repo.next_seq("trx")
        no_trx = f"TRX-{time_str}-{seq_trx:04d}"
        self.transaksi_repo.insert({
            "no_transaksi": no_trx,
            "pinjaman_id": pinjaman.id,
            "jenis": "PERPANJANGAN",
            "jumlah": biaya,
            "metode": metode_obj.kode,
            "status": "BERHASIL",
            "waktu": datetime.now().isoformat(),
            "petugas_id": petugas_id or 1,
            "keterangan": f"Biaya perpanjangan tenor kontrak {no_kontrak} hingga {tgl_baru}",
        })

        waktu_iso = datetime.now().isoformat()
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": f"Kas/Bank ({metode_obj.kode})",
            "debit": biaya,
            "kredit": Decimal("0"),
            "keterangan": f"Penerimaan biaya perpanjangan {no_kontrak}",
        })
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": "Pendapatan Perpanjangan Gadai",
            "debit": Decimal("0"),
            "kredit": biaya,
            "keterangan": f"Pendapatan perpanjangan {no_kontrak}",
        })

        p_row = self.perpanjangan_repo.get(perp_id)
        res = dict(p_row)
        res["biaya"] = Decimal(str(res["biaya"]))
        return res

    def ambil_barang(
        self,
        no_kontrak: str,
        petugas_id: int | None = None,
        hari_ini: date | None = None,
    ) -> dict:
        """Pengambilan barang agunan; hanya diperbolehkan jika pinjaman telah LUNAS."""
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        if row["status"] != "LUNAS":
            raise AturanBisnisError("Barang hanya dapat diambil jika pinjaman sudah LUNAS")

        self.pinjaman_repo.update(row["id"], {"status": "DIKEMBALIKAN"})
        self.barang_repo.update(row["barang_id"], {"status": "DIKEMBALIKAN"})

        gudang_rows = self.gudang_repo.find(pinjaman_id=row["id"])
        for g in gudang_rows:
            self.gudang_repo.update(g["id"], {"status": "DIKEMBALIKAN"})

        return {
            "no_kontrak": no_kontrak,
            "barang_id": row["barang_id"],
            "status": "DIKEMBALIKAN",
            "pesan": "Barang agunan berhasil diserahkan kembali kepada nasabah",
        }

    def deteksi_jatuh_tempo(self, hari_ini: date | None = None, cabang_id: int | None = None) -> int:
        """Mendeteksi pinjaman AKTIF yang melewati tenggat jatuh tempo dan mengubahnya menjadi JATUH_TEMPO."""
        today_str = str(hari_ini or date.today())
        clauses = ["status = 'AKTIF'", "tgl_jatuh_tempo < ?"]
        params = [today_str]

        if cabang_id is not None:
            clauses.append("cabang_id = ?")
            params.append(cabang_id)

        sql = f"SELECT id, barang_id FROM pinjaman WHERE " + " AND ".join(clauses)
        pinjaman_lewat = self.pinjaman_repo.query(sql, tuple(params))

        count = 0
        for p in pinjaman_lewat:
            self.pinjaman_repo.update(p["id"], {"status": "JATUH_TEMPO"})
            self.barang_repo.update(p["barang_id"], {"status": "JATUH_TEMPO"})
            count += 1

        return count

    def kirim_notifikasi_lelang(self, no_kontrak: str, hari_ini: date | None = None) -> dict:
        """Mengirim notifikasi tahapan lelang kepada nasabah yang wanprestasi setelah masa tenggang."""
        today = hari_ini or date.today()
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        if pinjaman.status != "JATUH_TEMPO":
            raise AturanBisnisError(f"Hanya pinjaman JATUH_TEMPO yang dapat dikirimi notifikasi lelang (status: {pinjaman.status})")

        masa_tenggang = int(self.parameter_repo.get_value("masa_tenggang_hari", 14))
        selisih_hari = (today - pinjaman.tgl_jatuh_tempo).days
        if selisih_hari < masa_tenggang:
            raise AturanBisnisError(
                f"Masa tenggang lelang belum berakhir. Diperlukan minimal {masa_tenggang} hari (saat ini {selisih_hari} hari)."
            )

        notif_list = self.notifikasi_repo.find(pinjaman_id=pinjaman.id)
        tahap_saat_ini = len(notif_list)

        if tahap_saat_ini >= 2:
            raise AturanBisnisError("Notifikasi peringatan lelang tahap maksimal (Tahap 2) telah dikirimkan")

        tahap_baru = tahap_saat_ini + 1
        pesan = (
            f"Pemberitahuan Peringatan Lelang Tahap {tahap_baru} untuk Kontrak {no_kontrak}. "
            f"Kewajiban pinjaman Anda telah jatuh tempo sejak {pinjaman.tgl_jatuh_tempo}. "
            f"Harap segera melakukan pelunasan atau perpanjangan agunan."
        )

        notif_id = self.notifikasi_repo.insert({
            "pinjaman_id": pinjaman.id,
            "tahap": tahap_baru,
            "tanggal": str(today),
            "pesan": pesan,
        })

        return self.notifikasi_repo.get(notif_id)

    def mulai_proses_lelang(self, no_kontrak: str, hari_ini: date | None = None) -> dict:
        """Memindahkan status pinjaman dan barang ke DALAM_PROSES_LELANG setelah syarat notifikasi terpenuhi."""
        today = hari_ini or date.today()
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        if row["status"] != "JATUH_TEMPO":
            raise AturanBisnisError(f"Pinjaman harus berstatus JATUH_TEMPO sebelum masuk proses lelang (status: {row['status']})")

        notif_list = self.notifikasi_repo.find(pinjaman_id=row["id"])
        if len(notif_list) < 2:
            raise AturanBisnisError(
                f"Pemberitahuan lelang belum memenuhi syarat prosedur. Harus mengirimkan notifikasi Tahap 1 dan 2 terlebih dahulu (saat ini {len(notif_list)} tahap)."
            )

        self.pinjaman_repo.update(row["id"], {"status": "DALAM_PROSES_LELANG"})
        self.barang_repo.update(row["barang_id"], {"status": "DALAM_PROSES_LELANG"})

        return self.detail_pinjaman(no_kontrak, hari_ini=today)

    def selesaikan_lelang(
        self,
        no_kontrak: str,
        harga_lelang: Decimal | str | int,
        hari_ini: date | None = None,
    ) -> dict:
        """
        Menyelesaikan eksekusi lelang agunan:
        - S = Hl - K (Selisih = Harga Lelang - Total Kewajiban)
        - S > 0: SURPLUS (hak nasabah)
        - S = 0: IMPAS
        - S < 0: DEFISIT (kerugian pegadaian)
        """
        today = hari_ini or date.today()
        row = self.pinjaman_repo.get_by_no_kontrak(no_kontrak)
        if not row:
            raise DataTidakDitemukanError(f"Pinjaman '{no_kontrak}' tidak ditemukan")

        if row["status"] != "DALAM_PROSES_LELANG":
            raise AturanBisnisError(f"Pinjaman harus dalam proses lelang untuk dapat diselesaikan (status: {row['status']})")

        hl = Decimal(str(harga_lelang)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if hl <= Decimal("0"):
            raise ValidasiError("Harga lelang harus lebih dari 0")

        pinjaman = self._sinkronkan_pinjaman_obj(row, today)
        kewajiban = pinjaman.hitung_total_kewajiban()
        selisih = hl - kewajiban

        if selisih > Decimal("0"):
            hasil = "SURPLUS"
            hak_nasabah = selisih
            kerugian = Decimal("0")
        elif selisih == Decimal("0"):
            hasil = "IMPAS"
            hak_nasabah = Decimal("0")
            kerugian = Decimal("0")
        else:
            hasil = "DEFISIT"
            hak_nasabah = Decimal("0")
            kerugian = abs(selisih)

        # Simpan ke tabel lelang
        self.lelang_repo.insert({
            "pinjaman_id": pinjaman.id,
            "harga_lelang": hl,
            "total_kewajiban": kewajiban,
            "selisih": selisih,
            "hasil": hasil,
            "hak_nasabah": hak_nasabah,
            "kerugian": kerugian,
            "tanggal": str(today),
        })

        # Update status pinjaman, barang, gudang
        self.pinjaman_repo.update(pinjaman.id, {"status": "TERLELANG"})
        self.barang_repo.update(pinjaman.barang_id, {"status": "TERLELANG"})

        gudang_rows = self.gudang_repo.find(pinjaman_id=pinjaman.id)
        for g in gudang_rows:
            self.gudang_repo.update(g["id"], {"status": "TERLELANG"})

        # Pembukuan Jurnal Akuntansi Lelang
        waktu_iso = datetime.now().isoformat()
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": "Kas Penerimaan Lelang",
            "debit": hl,
            "kredit": Decimal("0"),
            "keterangan": f"Hasil lelang agunan {no_kontrak}",
        })
        if kerugian > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Beban Kerugian Lelang Agunan",
                "debit": kerugian,
                "kredit": Decimal("0"),
                "keterangan": f"Defisit hasil lelang {no_kontrak}",
            })
        self.jurnal_repo.insert({
            "waktu": waktu_iso,
            "no_ref": no_kontrak,
            "akun": "Piutang Pinjaman Gadai",
            "debit": Decimal("0"),
            "kredit": pinjaman.sisa_pokok,
            "keterangan": f"Pelunasan piutang pokok via lelang {no_kontrak}",
        })
        if pinjaman.bunga_terutang > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Bunga Gadai",
                "debit": Decimal("0"),
                "kredit": pinjaman.bunga_terutang,
                "keterangan": f"Pelunasan bunga via lelang {no_kontrak}",
            })
        if pinjaman.denda_terutang > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Denda Keterlambatan",
                "debit": Decimal("0"),
                "kredit": pinjaman.denda_terutang,
                "keterangan": f"Pelunasan denda via lelang {no_kontrak}",
            })
        if pinjaman.biaya_admin_terutang > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Pendapatan Administrasi",
                "debit": Decimal("0"),
                "kredit": pinjaman.biaya_admin_terutang,
                "keterangan": f"Pelunasan admin via lelang {no_kontrak}",
            })
        if hak_nasabah > Decimal("0"):
            self.jurnal_repo.insert({
                "waktu": waktu_iso,
                "no_ref": no_kontrak,
                "akun": "Hutang Titipan Hak Nasabah (Surplus Lelang)",
                "debit": Decimal("0"),
                "kredit": hak_nasabah,
                "keterangan": f"Kelebihan hasil lelang {no_kontrak} milik nasabah",
            })

        return {
            "selisih": selisih,
            "hasil": hasil,
            "hak_nasabah": hak_nasabah,
            "kerugian": kerugian,
            "harga_lelang": hl,
            "total_kewajiban": kewajiban,
        }

    def daftar_transaksi(self, filter_dict: dict | None = None, cabang_id: int | None = None) -> list[dict]:
        """Pencarian riwayat transaksi berdasarkan filter no_kontrak, nasabah_id, jenis, tanggal, dan cari."""
        f = filter_dict or {}
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("p.cabang_id = ?")
            params.append(cabang_id)

        if f.get("no_kontrak"):
            clauses.append("p.no_kontrak = ?")
            params.append(f["no_kontrak"])

        if f.get("nasabah_id"):
            clauses.append("p.nasabah_id = ?")
            params.append(f["nasabah_id"])

        if f.get("jenis"):
            clauses.append("t.jenis = ?")
            params.append(f["jenis"].upper())

        if f.get("status"):
            clauses.append("t.status = ?")
            params.append(f["status"].upper())

        if f.get("dari"):
            clauses.append("DATE(t.waktu) >= ?")
            params.append(str(f["dari"]))

        if f.get("sampai"):
            clauses.append("DATE(t.waktu) <= ?")
            params.append(str(f["sampai"]))

        if f.get("cari"):
            clauses.append("(t.no_transaksi LIKE ? OR p.no_kontrak LIKE ? OR t.keterangan LIKE ?)")
            pattern = f"%{f['cari']}%"
            params.extend([pattern, pattern, pattern])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT t.*, p.no_kontrak, n.nama as nama_nasabah, u.nama as nama_petugas
            FROM transaksi t
            JOIN pinjaman p ON t.pinjaman_id = p.id
            JOIN nasabah n ON p.nasabah_id = n.id
            LEFT JOIN pengguna u ON t.petugas_id = u.id
            {where_sql}
            ORDER BY t.id DESC
        """
        rows = self.transaksi_repo.query(sql, tuple(params))
        hasil = []
        for r in rows:
            d = dict(r)
            d["jumlah"] = Decimal(str(d["jumlah"]))
            hasil.append(d)
        return hasil

    def cari_gudang(
        self,
        no_kontrak: str = "",
        nasabah_id: int | None = None,
        kode_barang: str = "",
        cabang_id: int | None = None,
    ) -> list[dict]:
        """Pencarian inventaris gudang berdasarkan kontrak, nasabah, atau kode barang."""
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("p.cabang_id = ?")
            params.append(cabang_id)

        if no_kontrak:
            clauses.append("p.no_kontrak = ?")
            params.append(no_kontrak)

        if nasabah_id is not None:
            clauses.append("p.nasabah_id = ?")
            params.append(nasabah_id)

        if kode_barang:
            clauses.append("g.kode_barang = ?")
            params.append(kode_barang)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT g.*, p.no_kontrak, b.deskripsi as deskripsi_barang, b.jenis as jenis_barang,
                   n.nama as nama_nasabah, c.nama as nama_cabang
            FROM gudang g
            JOIN pinjaman p ON g.pinjaman_id = p.id
            JOIN barang_jaminan b ON g.barang_id = b.id
            JOIN nasabah n ON p.nasabah_id = n.id
            JOIN cabang c ON p.cabang_id = c.id
            {where_sql}
            ORDER BY g.id DESC
        """
        return self.gudang_repo.query(sql, tuple(params))

    def daftar_lelang(self, cabang_id: int | None = None) -> list[dict]:
        """Daftar agunan yang telah diselesaikan lewat lelang eksekusi."""
        clauses = []
        params = []

        if cabang_id is not None:
            clauses.append("p.cabang_id = ?")
            params.append(cabang_id)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT l.*, p.no_kontrak, b.deskripsi as deskripsi_barang, b.jenis as jenis_barang,
                   n.nama as nama_nasabah, c.nama as nama_cabang
            FROM lelang l
            JOIN pinjaman p ON l.pinjaman_id = p.id
            JOIN barang_jaminan b ON p.barang_id = b.id
            JOIN nasabah n ON p.nasabah_id = n.id
            JOIN cabang c ON p.cabang_id = c.id
            {where_sql}
            ORDER BY l.id DESC
        """
        rows = self.lelang_repo.query(sql, tuple(params))
        hasil = []
        for r in rows:
            d = dict(r)
            d["harga_lelang"] = Decimal(str(d["harga_lelang"]))
            d["total_kewajiban"] = Decimal(str(d["total_kewajiban"]))
            d["selisih"] = Decimal(str(d["selisih"]))
            d["hak_nasabah"] = Decimal(str(d["hak_nasabah"]))
            d["kerugian"] = Decimal(str(d["kerugian"]))
            hasil.append(d)
        return hasil
