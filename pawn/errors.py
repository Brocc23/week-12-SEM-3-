"""Hierarki exception untuk sistem Pegadaian Digital Nusantara."""

class PawnError(Exception):
    """Exception dasar untuk semua error sistem gadai."""
    pass

class ValidasiError(PawnError):
    """Error validasi input data."""
    pass

class AksesDitolakError(PawnError):
    """Error otorisasi atau hak akses tidak mencukupi."""
    pass

# Alias untuk toleransi pengetikan pada spesifikasi
AkesDitolakError = AksesDitolakError

class DataTidakDitemukanError(PawnError):
    """Data yang dicari tidak ditemukan dalam basis data."""
    pass

class AturanBisnisError(PawnError):
    """Pelanggaran aturan bisnis sistem gadai."""
    pass
