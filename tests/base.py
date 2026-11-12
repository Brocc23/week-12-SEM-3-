"""Base test case providing an isolated temporary database for each test."""

import os
import shutil
import tempfile
import unittest

from pawn.seed import seed_if_empty
from pawn.services.facade import Aplikasi


class BaseTestCase(unittest.TestCase):
    """Base test fixture initializing a clean seeded temporary database per test."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.app = Aplikasi(self.db_path)
        seed_if_empty(self.app.db)

    def tearDown(self):
        self.app.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)
