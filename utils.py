import hashlib
import os
import logging
import re
from typing import List

_WINDOWS_RESERVED = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})
_INVALID_DIRNAME_CHARS = re.compile(r'[/\\:*?"<>|]')
_MAX_DIRNAME_LEN = 200


def get_logger(name: str = "AL_Batch_Manager") -> logging.Logger:
    """初始化并获取标准日志记录器"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def is_valid_cross_platform_dirname(name: str) -> bool:
    if not name or name in (".", ".."):
        return False
    if _INVALID_DIRNAME_CHARS.search(name):
        return False
    if name.endswith(" ") or name.endswith("."):
        return False
    if name.upper() in _WINDOWS_RESERVED:
        return False
    if len(name) > 255:
        return False
    return True


def legalize_dirname(name: str) -> str:
    legalized = name.strip().rstrip(".")
    if legalized.upper() in _WINDOWS_RESERVED:
        legalized = f"_{legalized}"
    if len(legalized) > _MAX_DIRNAME_LEN:
        legalized = legalized[:_MAX_DIRNAME_LEN].rstrip(". ")
    return legalized


def fallback_dirname(original_name: str) -> str:
    digest = hashlib.md5(original_name.encode("utf-8")).hexdigest()
    return f"bld_{digest}"


def resolve_export_basename(cleaned_name: str, original_name: str) -> str:
    legalized = legalize_dirname(cleaned_name)
    if is_valid_cross_platform_dirname(legalized):
        return legalized
    fallback = fallback_dirname(original_name)
    if not is_valid_cross_platform_dirname(fallback):
        get_logger().warning(
            "Fallback basename still invalid for %r, using raw digest prefix",
            original_name,
        )
    return fallback


def find_obj_files(root_dir: str, use_recursive: bool = True, max_depth: int = -1) -> List[str]:
    """
    基于 os.scandir 的高性能迭代遍历算法，避免深层递归爆栈。
    """
    obj_files = []
    root_dir = os.path.abspath(root_dir)

    # 堆栈元素: (当前路径, 当前深度)
    stack = [(root_dir, 0)]

    while stack:
        current_path, current_depth = stack.pop()

        # 深度控制
        if max_depth != -1 and current_depth > max_depth:
            continue

        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if entry.is_file() and entry.name.lower().endswith('.obj'):
                        obj_files.append(entry.path)
                    elif entry.is_dir() and use_recursive:
                        if max_depth == -1 or current_depth < max_depth:
                            stack.append((entry.path, current_depth + 1))
        except PermissionError:
            # 静默跳过无权限的目录
            continue

    return obj_files