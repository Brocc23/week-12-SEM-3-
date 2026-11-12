"""Facade Utama Aplikasi Pegadaian Digital Nusantara (UI Contract)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pawn.errors import (
    AksesDitolakError,
    AturanBisnisError,
    DataTidakDitemukanError,
    PawnError,
    ValidasiError,
)
from pawn.models.pengguna import Pengguna
from pawn.repository.database import Database
from pawn.repository.repos import (
    AuditRepo,
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
from pawn.services.audit_service import AuditService
from pawn.services.auth_service import AuthService
from pawn.services.gadai_service import GadaiService
from pawn.services.laporan_service import LaporanService
from pawn.services.nasabah_service import NasabahService
from pawn.services.penaksiran_service import PenaksiranService


class Aplikasi:
    """
    Facade tunggal penghubung antara UI (Presentation Layer) dan Business Logic/Repository.
    Mengimplementasikan RBAC, isolasi cabang, atomisitas transaksi, dan jejak audit menyeluruh.
    """

    def __init__(self, db_path: str = "pegadaian.db"):
        self.db = Database(db_path)
        self.db.init_schema()

        # Repositories
        self.cabang_repo = CabangRepo(self.db)
        self.pengguna_repo = PenggunaRepo(self.db)
        self.nasabah_repo = NasabahRepo(self.db)
        self.barang_repo = BarangRepo(self.db)
        self.pinjaman_repo = PinjamanRepo(self.db)
        self.transaksi_repo = TransaksiRepo(self.db)
        self.perpanjangan_repo = PerpanjanganRepo(self.db)
        self.gudang_repo = GudangRepo(self.db)
        self.notifikasi_repo = NotifikasiRepo(self.db)
        self.lelang_repo = LelangRepo(self.db)
        self.parameter_repo = ParameterRepo(self.db)
        self.audit_repo = AuditRepo(self.db)
        self.jurnal_repo = JurnalRepo(self.db)

        # Domain Services
        self.audit_service = AuditService(self.audit_repo, self.jurnal_repo)
        self.auth_service = AuthService(self.pengguna_repo, self.cabang_repo)
        self.penaksiran_service = PenaksiranService(self.parameter_repo)
        self.nasabah_service = NasabahService(
            self.nasabah_repo,
            self.cabang_repo,
            self.pinjaman_repo,
            self.transaksi_repo,
        )
        self.gadai_service = GadaiService(
            self.pinjaman_repo,
            self.barang_repo,
            self.nasabah_repo,
            self.cabang_repo,
            self.pengguna_repo,
            self.transaksi_repo,
            self.perpanjangan_repo,
            self.gudang_repo,
            self.notifikasi_repo,
            self.lelang_repo,
            self.parameter_repo,
            self.jurnal_repo,
            self.penaksiran_service,
        )
        self.laporan_service = LaporanService(
            self.jurnal_repo,
            self.transaksi_repo,
            self.lelang_repo,
            self.perpanjangan_repo,
            self.barang_repo,
        )

        # Session & Simulation State
        self._pengguna_aktif: Pengguna | None = None
        self._tanggal_simulasi: date | None = None

    # =========================================================================
    # SIMULATION & DATE HELPERS
    # =========================================================================

    def set_tanggal_simulasi(self, tgl: date | str | None) -> None:
        """Mengatur tanggal simulasi sistem untuk keperluan demo jatuh tempo dan lelang."""
        if tgl is None:
            self._tanggal_simulasi = None
        elif isinstance(tgl, str):
            self._tanggal_simulasi = date.fromisoformat(tgl)
        elif isinstance(tgl, date):
            self._tanggal_simulasi = tgl
        self._catat_audit("SET_TANGGAL_SIMULASI", f"Tanggal simulasi diatur ke {self._tanggal_simulasi}")

    def hari_ini(self) -> date:
        """Mengembalikan tanggal sistem saat ini (atau tanggal simulasi jika diaktifkan)."""
        return self._tanggal_simulasi or date.today()

    # =========================================================================
    # AUDIT & PERMISSION GUARDS
    # =========================================================================

    def _catat_audit(self, aksi: str, detail: str) -> None:
        """Pencatatan log audit internal yang tidak mengganggu alur utama bila terjadi exception."""
        user_id = self._pengguna_aktif.id if self._pengguna_aktif else None
        waktu = datetime.now().isoformat()
        try:
            self.audit_service.catat_audit(user_id, aksi, detail, waktu)
        except Exception:
            pass

    def _wajib_login(self) -> Pengguna:
        """Memastikan pengguna telah terotentikasi sebelum memanggil aksi."""
        if not self._pengguna_aktif:
            self._catat_audit("AKSES_DITOLAK", "Aksi membutuhkan login terlebih dahulu")
            raise AksesDitolakError("Silakan login terlebih dahulu untuk mengakses fitur ini")
        return self._pengguna_aktif

    def _wajib_izin(self, izin: str) -> Pengguna:
        """Memastikan pengguna aktif memiliki izin RBAC tertentu."""
        user = self._wajib_login()
        if izin not in user.hak_akses():
            self._catat_audit("AKSES_DITOLAK", f"Izin '{izin}' ditolak untuk role {user.role}")
            raise AksesDitolakError(f"Akses ditolak: pengguna tidak memiliki izin '{izin}'")
        return user

    def _cabang_isolasi(self) -> int | None:
        """Mengembalikan cabang_id untuk pembatasan data bila role bukan ADMIN."""
        if self._pengguna_aktif and self._pengguna_aktif.role != "ADMIN":
            return self._pengguna_aktif.cabang_id
        return None

    # =========================================================================
    # AUTHENTICATION
    # =========================================================================

    def login(self, username: str, password: str) -> dict:
        """Otentikasi pengguna ke sistem (tidak memerlukan login sebelumnya)."""
        try:
            user = self.auth_service.login(username, password)
            self._pengguna_aktif = user
            self._catat_audit("LOGIN_BERHASIL", f"Pengguna {username} berhasil login")
            return user.to_dict()
        except Exception as e:
            self._catat_audit("LOGIN_GAGAL", f"Percobaan login gagal untuk {username}: {e}")
            raise

    def logout(self) -> None:
        """Mengakhiri sesi pengguna aktif."""
        username = self._pengguna_aktif.username if self._pengguna_aktif else "Anonim"
        self._catat_audit("LOGOUT", f"Pengguna {username} telah logout")
        self._pengguna_aktif = None

    @property
    def pengguna_aktif(self) -> dict | None:
        """Informasi pengguna yang sedang aktif dalam sesi."""
        return self._pengguna_aktif.to_dict() if self._pengguna_aktif else None

    def hak_akses(self) -> set[str]:
        """Mengembalikan himpunan izin (permissions) pengguna aktif."""
        if not self._pengguna_aktif:
            return set()
        return self._pengguna_aktif.hak_akses()

    # =========================================================================
    # ADMIN
    # =========================================================================

    def daftar_pengguna(self) -> list[dict]:
        """Menampilkan daftar pengguna sistem (khusus ADMIN)."""
        self._wajib_izin("admin")
        return self.auth_service.daftar_pengguna()

    def tambah_pengguna(
        self,
        username: str,
        password: str,
        nama: str,
        role: str,
        cabang_id: int | None = None,
    ) -> dict:
        """Menambahkan akun pengguna baru (khusus ADMIN)."""
        self._wajib_izin("admin")
        with self.db.transaction():
            res = self.auth_service.tambah_pengguna(username, password, nama, role, cabang_id)
            self._catat_audit("TAMBAH_PENGGUNA", f"Menambahkan pengguna {username} dengan role {role}")
            clean = dict(res)
            clean.pop("password_hash", None)
            clean.pop("salt", None)
            return clean

    def ubah_aktif(self, user_id: int, aktif: int | bool) -> None:
        """Mengaktifkan atau menonaktifkan akun pengguna (khusus ADMIN)."""
        self._wajib_izin("admin")
        with self.db.transaction():
            self.auth_service.ubah_aktif(user_id, aktif)
            self._catat_audit("UBAH_AKTIF_PENGGUNA", f"Mengubah status aktif user ID {user_id} ke {aktif}")

    def daftar_cabang(self) -> list[dict]:
        """Menampilkan seluruh cabang operasional pegadaian."""
        self._wajib_login()
        return self.cabang_repo.all()

    def tambah_cabang(self, kode: str, nama: str, alamat: str) -> dict:
        """Menambahkan kantor cabang operasional baru (khusus ADMIN)."""
        self._wajib_izin("admin")
        kode = (kode or "").upper().strip()
        if not kode or not nama:
            raise ValidasiError("Kode dan nama cabang tidak boleh kosong")

        with self.db.transaction():
            cid = self.cabang_repo.insert({"kode": kode, "nama": nama, "alamat": alamat})
            self._catat_audit("TAMBAH_CABANG", f"Menambahkan cabang {kode} - {nama}")
            return self.cabang_repo.get(cid)

    def daftar_parameter(self) -> list[dict]:
        """Mengambil seluruh parameter konfigurasi sistem."""
        self._wajib_login()
        rows = self.parameter_repo.all()
        return [{"kunci": r["kunci"], "nilai": r["nilai"]} for r in rows]

    def ubah_parameter(self, kunci: str, nilai: Any) -> None:
        """Mengubah nilai parameter konfigurasi bisnis (khusus ADMIN)."""
        self._wajib_izin("admin")
        with self.db.transaction():
            self.parameter_repo.set_value(kunci, str(nilai))
            self._catat_audit("UBAH_PARAMETER", f"Parameter '{kunci}' diubah menjadi '{nilai}'")

    def lihat_audit_log(self, limit: int = 500) -> list[dict]:
        """Melihat catatan log audit integritas sistem (khusus ADMIN)."""
        self._wajib_izin("admin")
        return self.audit_service.lihat_audit_log(limit=limit)

    def backup_database(self, path: str) -> None:
        """Membuat salinan cadangan berkas database SQLite (khusus ADMIN)."""
        self._wajib_izin("admin")
        self.db.backup(path)
        self._catat_audit("BACKUP_DB", f"Database berhasil dibackup ke {path}")

    def restore_database(self, path: str) -> None:
        """Memulihkan berkas database dari berkas cadangan (khusus ADMIN)."""
        self._wajib_izin("admin")
        self.db.restore(path)
        self._catat_audit("RESTORE_DB", f"Database berhasil dipulihkan dari {path}")

    # =========================================================================
    # NASABAH
    # =========================================================================

    def daftar_nasabah(self, cari: str = "") -> list[dict]:
        """Pencarian dan daftar nasabah dengan isolasi cabang otomatis."""
        self._wajib_izin("nasabah.kelola")
        return self.nasabah_service.daftar_nasabah(cari=cari, cabang_id=self._cabang_isolasi())

    def tambah_nasabah(
        self,
        nik: str,
        nama: str,
        alamat: str,
        telepon: str,
        email: str,
    ) -> dict:
        """Mendaftarkan nasabah baru pada cabang pengguna aktif."""
        user = self._wajib_izin("nasabah.kelola")
        cabang_id = user.cabang_id or 1  # Default ke cabang 1 bila admin tidak terikat cabang

        with self.db.transaction():
            res = self.nasabah_service.tambah_nasabah(
                cabang_id=cabang_id,
                nik=nik,
                nama=nama,
                alamat=alamat,
                telepon=telepon,
                email=email,
                tgl_daftar=self.hari_ini(),
            )
            self._catat_audit("TAMBAH_NASABAH", f"Nasabah baru terdaftar: {res['kode']} - {res['nama']}")
            return res

    def ubah_status_nasabah(self, nasabah_id: int, status: str) -> None:
        """Mengubah status nasabah (AKTIF / DITANGGUHKAN)."""
        self._wajib_izin("nasabah.kelola")
        with self.db.transaction():
            self.nasabah_service.ubah_status_nasabah(nasabah_id, status)
            self._catat_audit("UBAH_STATUS_NASABAH", f"Status nasabah ID {nasabah_id} diubah ke {status}")

    def hapus_nasabah(self, nasabah_id: int) -> None:
        """Menghapus nasabah bila tidak memiliki pinjaman berjalan."""
        self._wajib_izin("nasabah.kelola")
        with self.db.transaction():
            self.nasabah_service.hapus_nasabah(nasabah_id)
            self._catat_audit("HAPUS_NASABAH", f"Nasabah ID {nasabah_id} berhasil dihapus")

    def riwayat_nasabah(self, nasabah_id: int) -> dict:
        """Menampilkan riwayat kontrak dan transaksi lengkap seorang nasabah."""
        self._wajib_izin("nasabah.kelola")
        return self.nasabah_service.riwayat_nasabah(nasabah_id)

    def nasabah_menunggak(self) -> list[dict]:
        """Daftar nasabah yang pinjamannya telah jatuh tempo."""
        self._wajib_izin("nasabah.kelola")
        return self.nasabah_service.nasabah_menunggak(
            cabang_id=self._cabang_isolasi(),
            hari_ini=self.hari_ini(),
        )

    # =========================================================================
    # PENAKSIRAN
    # =========================================================================

    def hitung_taksiran(self, jenis: str, atribut: dict) -> dict:
        """
        Kalkulasi nilai taksiran agunan dan batas pinjaman maksimal (LTV).
        Dapat dipanggil oleh PENAKSIR atau ADMIN.
        """
        self._wajib_izin("taksir")
        return self.penaksiran_service.hitung_taksiran(jenis, atribut)

    # =========================================================================
    # GADAI & KASIR
    # =========================================================================

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
    ) -> dict:
        """
        Alur transaksi gadai terintegrasi 9 langkah bisnis:
        verifikasi -> taksir -> limit check -> kontrak -> barang -> pinjaman -> transaksi -> jurnal -> gudang.
        """
        user = self._wajib_izin("gadai")
        with self.db.transaction():
            res = self.gadai_service.ajukan_gadai(
                nasabah_id=nasabah_id,
                jenis=jenis,
                deskripsi=deskripsi,
                atribut=atribut,
                jumlah_pinjaman=jumlah_pinjaman,
                tenor_hari=tenor_hari,
                lokasi_gudang=lokasi_gudang,
                kondisi_barang=kondisi_barang,
                penaksir_id=penaksir_id or (user.id if user.role == "PENAKSIR" else None),
                petugas_id=user.id,
                cabang_id=user.cabang_id,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit(
                "AJUKAN_GADAI",
                f"Gadai baru kontrak {res['no_kontrak']} senilai Rp {res['pokok']:,}",
            )
            return res

    def daftar_pinjaman(
        self,
        status: str | None = None,
        cari: str = "",
        nasabah_id: int | None = None,
    ) -> list[dict]:
        """Menampilkan daftar pinjaman dengan filter status dan pencarian."""
        self._wajib_izin("gadai")
        return self.gadai_service.daftar_pinjaman(
            status=status,
            cari=cari,
            nasabah_id=nasabah_id,
            cabang_id=self._cabang_isolasi(),
        )

    def detail_pinjaman(self, no_kontrak: str) -> dict:
        """Mengambil rincian kontrak pinjaman berserta total kewajiban terkini."""
        self._wajib_izin("gadai")
        return self.gadai_service.detail_pinjaman(no_kontrak, hari_ini=self.hari_ini())

    def hitung_kewajiban(self, no_kontrak: str) -> dict:
        """Menghitung rincian kewajiban pinjaman saat ini (pokok, bunga, admin, denda)."""
        self._wajib_login()
        return self.gadai_service.hitung_kewajiban(no_kontrak, hari_ini=self.hari_ini())

    def daftar_metode(self) -> list[str]:
        """Daftar metode pembayaran resmi sistem pegadaian."""
        return ["TUNAI", "TRANSFER", "QRIS", "EWALLET"]

    def bayar_angsuran(
        self,
        no_kontrak: str,
        jumlah: Decimal | str | int,
        metode: str,
    ) -> dict:
        """Pembayaran cicilan pinjaman menggunakan waterfall alokasi biaya."""
        user = self._wajib_izin("bayar")
        with self.db.transaction():
            res = self.gadai_service.bayar_angsuran(
                no_kontrak=no_kontrak,
                jumlah=jumlah,
                metode=metode,
                petugas_id=user.id,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit(
                "BAYAR_ANGSURAN",
                f"Angsuran kontrak {no_kontrak} sejumlah Rp {res['jumlah']:,} via {metode}",
            )
            return res

    def lunasi(
        self,
        no_kontrak: str,
        jumlah: Decimal | str | int,
        metode: str,
    ) -> dict:
        """Pelunasan pinjaman penuh (ditolak bila pembayaran kurang dari kewajiban)."""
        user = self._wajib_izin("bayar")
        with self.db.transaction():
            res = self.gadai_service.lunasi(
                no_kontrak=no_kontrak,
                jumlah=jumlah,
                metode=metode,
                petugas_id=user.id,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit(
                "LUNASI_PINJAMAN",
                f"Pelunasan kontrak {no_kontrak} sejumlah Rp {res['jumlah']:,} via {metode}",
            )
            return res

    def perpanjang(self, no_kontrak: str, metode: str) -> dict:
        """Perpanjangan masa tenor pinjaman (bunga dan denda wajib telah lunas)."""
        user = self._wajib_izin("bayar")
        with self.db.transaction():
            res = self.gadai_service.perpanjang(
                no_kontrak=no_kontrak,
                metode=metode,
                petugas_id=user.id,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit(
                "PERPANJANG_TENOR",
                f"Perpanjangan tenor kontrak {no_kontrak} dengan biaya Rp {res['biaya']:,}",
            )
            return res

    def ambil_barang(self, no_kontrak: str) -> dict:
        """Pengambilan kembali agunan nasabah setelah pinjaman LUNAS."""
        user = self._wajib_izin("gadai")
        with self.db.transaction():
            res = self.gadai_service.ambil_barang(
                no_kontrak=no_kontrak,
                petugas_id=user.id,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit("AMBIL_BARANG", f"Agunan kontrak {no_kontrak} telah diserahkan kembali")
            return res

    def daftar_transaksi(self, filter: dict | None = None) -> list[dict]:
        """Pencarian riwayat transaksi keuangan pada kasir."""
        self._wajib_izin("bayar")
        return self.gadai_service.daftar_transaksi(
            filter_dict=filter,
            cabang_id=self._cabang_isolasi(),
        )

    # =========================================================================
    # GUDANG
    # =========================================================================

    def cari_gudang(
        self,
        no_kontrak: str = "",
        nasabah_id: int | None = None,
        kode_barang: str = "",
    ) -> list[dict]:
        """Pencarian fisik agunan di gudang penyimpanan cabang."""
        self._wajib_izin("gadai")
        return self.gadai_service.cari_gudang(
            no_kontrak=no_kontrak,
            nasabah_id=nasabah_id,
            kode_barang=kode_barang,
            cabang_id=self._cabang_isolasi(),
        )

    # =========================================================================
    # JATUH TEMPO & LELANG
    # =========================================================================

    def deteksi_jatuh_tempo(self) -> int:
        """Deteksi otomatis kontrak yang melewati jatuh tempo (AKTIF -> JATUH_TEMPO)."""
        self._wajib_login()
        with self.db.transaction():
            cnt = self.gadai_service.deteksi_jatuh_tempo(
                hari_ini=self.hari_ini(),
                cabang_id=self._cabang_isolasi(),
            )
            if cnt > 0:
                self._catat_audit("DETEKSI_JATUH_TEMPO", f"{cnt} kontrak diperbarui ke JATUH_TEMPO")
            return cnt

    def kirim_notifikasi_lelang(self, no_kontrak: str) -> dict:
        """Mengirimkan surat notifikasi peringatan lelang (Tahap 1 atau Tahap 2)."""
        self._wajib_izin("lelang")
        with self.db.transaction():
            res = self.gadai_service.kirim_notifikasi_lelang(no_kontrak, hari_ini=self.hari_ini())
            self._catat_audit(
                "KIRIM_NOTIFIKASI_LELANG",
                f"Notifikasi lelang tahap {res['tahap']} terkirim untuk kontrak {no_kontrak}",
            )
            return res

    def mulai_proses_lelang(self, no_kontrak: str) -> dict:
        """Memulai proses lelang publik setelah seluruh tahapan notifikasi dipenuhi."""
        self._wajib_izin("lelang")
        with self.db.transaction():
            res = self.gadai_service.mulai_proses_lelang(no_kontrak, hari_ini=self.hari_ini())
            self._catat_audit("MULAI_LELANG", f"Kontrak {no_kontrak} dimasukkan ke DALAM_PROSES_LELANG")
            return res

    def selesaikan_lelang(
        self,
        no_kontrak: str,
        harga_lelang: Decimal | str | int,
    ) -> dict:
        """Menyelesaikan eksekusi lelang barang jaminan dan menghitung surplus/defisit."""
        self._wajib_izin("lelang")
        with self.db.transaction():
            res = self.gadai_service.selesaikan_lelang(
                no_kontrak,
                harga_lelang,
                hari_ini=self.hari_ini(),
            )
            self._catat_audit(
                "SELESAIKAN_LELANG",
                f"Lelang {no_kontrak} selesai: Hasil={res['hasil']}, Selisih=Rp {res['selisih']:,}",
            )
            return res

    def daftar_lelang(self) -> list[dict]:
        """Melihat riwayat hasil penyelesaian lelang agunan."""
        self._wajib_izin("lelang")
        return self.gadai_service.daftar_lelang(cabang_id=self._cabang_isolasi())

    # =========================================================================
    # LAPORAN
    # =========================================================================

    def laporan_laba_rugi(self, dari: date | str, sampai: date | str) -> dict:
        """Laporan kinerja pendapatan dan beban operasional pada rentang tanggal."""
        self._wajib_izin("laporan")
        return self.laporan_service.laporan_laba_rugi(
            dari=dari,
            sampai=sampai,
            cabang_id=self._cabang_isolasi(),
        )

    def laporan_aset_jaminan(self) -> list[dict]:
        """Laporan rekapitulasi seluruh nilai aset agunan yang berada di tangan pegadaian."""
        self._wajib_izin("laporan")
        return self.laporan_service.laporan_aset_jaminan(cabang_id=self._cabang_isolasi())

    def export_laporan_csv(self, rows: list[dict], path: str) -> None:
        """Mengekspor daftar baris data laporan ke dalam berkas CSV."""
        self._wajib_izin("laporan")
        self.laporan_service.export_laporan_csv(rows, path)
        self._catat_audit("EXPORT_CSV", f"Ekspor laporan CSV ({len(rows)} baris) ke {path}")
