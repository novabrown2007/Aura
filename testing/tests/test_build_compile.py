"""Automated tests for `test_build_compile` behavior and regression coverage."""

import py_compile
from pathlib import Path
import tempfile
import os
import unittest


class BuildCompileTests(unittest.TestCase):
    """Test cases covering `BuildCompileTests` behavior and expected command/runtime outcomes."""
    def test_python_files_compile(self):
        """Validate that python files compile behaves as expected."""
        root = Path(__file__).resolve().parents[2]
        excludes = {"venv", ".venv", "__pycache__", ".git", ".idea", "build", "dist", "logs"}
        failures = []

        for py_file in root.rglob("*.py"):
            if any(part in excludes for part in py_file.parts):
                continue
            temp_pyc = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pyc") as handle:
                    temp_pyc = handle.name
                py_compile.compile(str(py_file), cfile=temp_pyc, doraise=True)
            except Exception as error:
                failures.append(f"{py_file}: {error}")
            finally:
                if temp_pyc and os.path.exists(temp_pyc):
                    try:
                        os.remove(temp_pyc)
                    except OSError:
                        pass

        if failures:
            self.fail("Compilation failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()

