import warnings

from pydantic.warnings import PydanticDeprecatedSince20

warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn")
warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

from . import agent
from . import retrieve
from . import summary
from . import vector_store

__version__ = "0.1.10"
