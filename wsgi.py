import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "myqsl_app",
    Path(__file__).parent / "MyQSL.py"
)
module = importlib.util.module_from_spec(spec)
sys.modules["myqsl_app"] = module
spec.loader.exec_module(module)

app = module.app
