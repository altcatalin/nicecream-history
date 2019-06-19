from typing import Any


def issubclass_py37(cls: Any, cls_info: Any) -> bool:
    try:
        return issubclass(cls, cls_info)
    except TypeError:
        return False
