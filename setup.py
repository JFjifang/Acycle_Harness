"""Include the canonical MATLAB sources in installed wheels without duplication."""
from pathlib import Path
from shutil import copytree
from setuptools import setup
from setuptools.command.build_py import build_py


class MatlabBuild(build_py):
    def run(self):
        super().run()
        copytree(Path(__file__).parent / 'matlab', Path(self.build_lib) / 'acycle_deepseek' / 'matlab', dirs_exist_ok=True)


setup(cmdclass={'build_py': MatlabBuild})
