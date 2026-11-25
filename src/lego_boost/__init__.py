"""Old name of the `hubbit` package, kept for the 0.2 releases only.

`import lego_boost` and `from lego_boost.kid import Robot` still work but warn: change them
to `hubbit` (for example `from hubbit.kid import Robot`). This shim goes away in 0.3.0.
"""

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

warnings.warn(
    "'lego_boost' is now called 'hubbit': change 'lego_boost' to 'hubbit' in your imports.",
    DeprecationWarning,
    stacklevel=2,
)


class _AliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve `lego_boost.X` as the very same module object as `hubbit.X` (no second copy)."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(__name__ + "."):
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return importlib.import_module("hubbit" + spec.name[len(__name__) :])

    def exec_module(self, module):
        pass  # already executed as hubbit.X


if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

from hubbit import *  # noqa: E402, F403
from hubbit import __all__  # noqa: E402, F401
