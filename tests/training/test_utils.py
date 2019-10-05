import unittest
import contextlib
from delira.training.utils import create_iterator
import os

from ..utils import check_for_no_backend


class IteratorWrapperTest(unittest.TestCase):

    @unittest.skipUnless(check_for_no_backend(),
                         "Test should be only executed if no "
                         "backend was installed")
    def test_wrapper_verbose(self):
        with open("logging_tmp.txt", "w") as f:
            with contextlib.redirect_stderr(f):
                iterable = range(500)

                for idx, item in create_iterator(iterable, True, enum=True):
                    pass

        with open("logging_tmp.txt", "r") as f:
            content = f.readlines()

        for line in content:
            self.assertTrue(bool(line))

    @unittest.skipUnless(check_for_no_backend(),
                         "Test should be only executed if no "
                         "backend was installed")
    def test_wrapper_non_verbose(self):
        with open("logging_tmp.txt", "w") as f:
            with contextlib.redirect_stderr(f):
                iterable = range(500)

                for idx, item in create_iterator(iterable, False, enum=True):
                    pass

        with open("logging_tmp.txt", "r") as f:
            content = f.readlines()

        for line in content:
            self.assertFalse(bool(line))

    def tearDown(self) -> None:
        os.remove("logging_tmp.txt")


if __name__ == '__main__':
    unittest.main()
