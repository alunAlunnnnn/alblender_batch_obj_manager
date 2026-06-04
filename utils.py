import os
import logging
from typing import List


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