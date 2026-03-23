import py_compile
from pathlib import Path
import unittest


class BuildCompileTests(unittest.TestCase):
    def test_python_files_compile(self):
        root = Path(__file__).resolve().parents[1]
        excludes = {"venv", "__pycache__", ".git", ".idea"}
        failures = []

        for py_file in root.rglob("*.py"):
            if any(part in excludes for part in py_file.parts):
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
            except Exception as error:
                failures.append(f"{py_file}: {error}")

        if failures:
            self.fail("Compilation failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()

