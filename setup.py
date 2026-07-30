from setuptools import setup
from setuptools.command.build_py import build_py


class ForcedBuildPy(build_py):
    """Never let a stale local build/lib tree override current package sources."""

    def finalize_options(self):
        super().finalize_options()
        self.force = True


setup(cmdclass={"build_py": ForcedBuildPy})
