"""Repository implementations for database persistence and querying."""

from decimal import Decimal
from typing import Any

from pawn.repository.database import Database


class BaseRepository:
    """Base generic repository with standard CRUD, filters, and sequence generator."""

    table: str = ""

    def __init__(self, db: Database):
        self.db = db

    def insert(self, data: dict[str, Any]) -> int:
        """Insert a row and return its generated integer ID."""
        clean_data = {
            k: (str(v) if isinstance(v, Decimal) else v) for k, v in data.items()
        }
        keys = list(clean_data.keys())
        cols = ", ".join(keys)
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders})"
        cursor = self.db.connection().execute(sql, tuple(clean_data.values()))
        return cursor.lastrowid

    def update(self, id: int, data: dict[str, Any]) -> None:
        """Update a row identified by primary key id."""
        if not data:
            return
        clean_data = {
            k: (str(v) if isinstance(v, Decimal) else v) for k, v in data.items()
        }
        cols = ", ".join([f"{k} = ?" for k in clean_data.keys()])
        sql = f"UPDATE {self.table} SET {cols} WHERE id = ?"
        params = tuple(clean_data.values()) + (id,)
        self.db.connection().execute(sql, params)

    def get(self, id: int) -> dict[str, Any] | None:
        """Fetch a single record by primary key id."""
        cursor = self.db.connection().execute(
            f"SELECT * FROM {self.table} WHERE id = ?", (id,)
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def find(self, **where: Any) -> list[dict[str, Any]]:
        """Find records matching equality filters (handles IS NULL for None)."""
        if not where:
            return self.all()
        clauses: list[str] = []
        params: list[Any] = []
        for k, v in where.items():
            if v is None:
                clauses.append(f"{k} IS NULL")
            else:
                clauses.append(f"{k} = ?")
                params.append(str(v) if isinstance(v, Decimal) else v)
        sql = f"SELECT * FROM {self.table} WHERE " + " AND ".join(clauses)
        cursor = self.db.connection().execute(sql, tuple(params))
        return [dict(r) for r in cursor.fetchall()]

    def all(self) -> list[dict[str, Any]]:
        """Fetch all records in the table."""
        cursor = self.db.connection().execute(f"SELECT * FROM {self.table}")
        return [dict(r) for r in cursor.fetchall()]

    def delete(self, id: int) -> None:
        """Delete a record by primary key id."""
        self.db.connection().execute(f"DELETE FROM {self.table} WHERE id = ?", (id,))

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Run custom SQL query with tuple parameters."""
        clean_params = tuple(str(p) if isinstance(p, Decimal) else p for p in params)
        cursor = self.db.connection().execute(sql, clean_params)
        return [dict(r) for r in cursor.fetchall()]

    def next_seq(self, key: str) -> int:
        """Atomic persistent sequence counter stored in the parameter table."""
        param_key = f"seq_{key}"
        cursor = self.db.connection().execute(
            "INSERT INTO parameter (kunci, nilai) VALUES (?, '1') "
            "ON CONFLICT(kunci) DO UPDATE SET nilai = CAST(nilai AS INTEGER) + 1 "
            "RETURNING CAST(nilai AS INTEGER)",
            (param_key,),
        )
        row = cursor.fetchone()
        return int(row[0])


class CabangRepo(BaseRepository):
    table = "cabang"

    def get_by_kode(self, kode: str) -> dict[str, Any] | None:
        rows = self.find(kode=kode)
        return rows[0] if rows else None


class PenggunaRepo(BaseRepository):
    table = "pengguna"

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        rows = self.find(username=username)
        return rows[0] if rows else None


class NasabahRepo(BaseRepository):
    table = "nasabah"

    def get_by_kode(self, kode: str) -> dict[str, Any] | None:
        rows = self.find(kode=kode)
        return rows[0] if rows else None

    def get_by_nik(self, nik: str) -> dict[str, Any] | None:
        rows = self.find(nik=nik)
        return rows[0] if rows else None


class BarangRepo(BaseRepository):
    table = "barang_jaminan"

    def get_by_kode(self, kode: str) -> dict[str, Any] | None:
        rows = self.find(kode=kode)
        return rows[0] if rows else None


class PinjamanRepo(BaseRepository):
    table = "pinjaman"

    def get_by_no_kontrak(self, no_kontrak: str) -> dict[str, Any] | None:
        rows = self.find(no_kontrak=no_kontrak)
        return rows[0] if rows else None


class TransaksiRepo(BaseRepository):
    table = "transaksi"

    def get_by_no_transaksi(self, no_transaksi: str) -> dict[str, Any] | None:
        rows = self.find(no_transaksi=no_transaksi)
        return rows[0] if rows else None


class PerpanjanganRepo(BaseRepository):
    table = "perpanjangan"


class GudangRepo(BaseRepository):
    table = "gudang"

    def get_by_kode_barang(self, kode_barang: str) -> dict[str, Any] | None:
        rows = self.find(kode_barang=kode_barang)
        return rows[0] if rows else None


class NotifikasiRepo(BaseRepository):
    table = "notifikasi_lelang"


class LelangRepo(BaseRepository):
    table = "lelang"

    def get_by_pinjaman_id(self, pinjaman_id: int) -> dict[str, Any] | None:
        rows = self.find(pinjaman_id=pinjaman_id)
        return rows[0] if rows else None


class ParameterRepo(BaseRepository):
    table = "parameter"

    def get(self, kunci: Any) -> dict[str, Any] | None:
        cursor = self.db.connection().execute(
            "SELECT * FROM parameter WHERE kunci = ?", (str(kunci),)
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def get_value(self, kunci: str, default: Any = None) -> Decimal | str | None:
        """Retrieve parameter as Decimal if numeric, or string otherwise."""
        row = self.get(kunci)
        if row is None:
            return default
        val = row["nilai"]
        try:
            return Decimal(val)
        except Exception:
            return val

    def set_value(self, kunci: str, nilai: Any) -> None:
        """Upsert a key-value parameter pair."""
        val_str = str(nilai) if isinstance(nilai, Decimal) else str(nilai)
        self.db.connection().execute(
            "INSERT INTO parameter (kunci, nilai) VALUES (?, ?) "
            "ON CONFLICT(kunci) DO UPDATE SET nilai = excluded.nilai",
            (kunci, val_str),
        )

    def update(self, id: Any, data: dict[str, Any]) -> None:
        if "nilai" in data:
            self.set_value(str(id), data["nilai"])
        else:
            super().update(id, data)

    def delete(self, id: Any) -> None:
        self.db.connection().execute("DELETE FROM parameter WHERE kunci = ?", (str(id),))


class AuditRepo(BaseRepository):
    table = "audit_log"

    def update(self, id: int, data: dict[str, Any]) -> None:
        raise PermissionError("audit_log is immutable; update not allowed")

    def delete(self, id: int) -> None:
        raise PermissionError("audit_log is immutable; delete not allowed")


class JurnalRepo(BaseRepository):
    table = "jurnal"
