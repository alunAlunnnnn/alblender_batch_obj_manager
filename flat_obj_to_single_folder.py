import os
import shutil
import concurrent.futures
from pathlib import Path
import logging
import time

# 配置日志输出格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(threadName)-10s | %(message)s',
    datefmt='%H:%M:%S'
)

# MTL 文件中可能出现的所有贴图通道关键字（全部小写用于匹配）
TEXTURE_KEYWORDS = {
    'map_ka', 'map_kd', 'map_ks', 'map_ns', 'map_d',
    'map_bump', 'bump', 'disp', 'decal', 'refl', 'norm'
}


def extract_texture_path(line: str) -> str:
    """
    从 MTL 的贴图定义行中提取纯净的文件路径。
    处理带有参数的情况，例如: map_Bump -bm 1.0 my_texture.png
    """
    parts = line.split()
    # 如果没有使用参数（最常见情况），直接返回第一个空格后的所有内容（支持包含空格的文件名）
    if len(parts) >= 2 and not parts[1].startswith('-'):
        return line.split(maxsplit=1)[1].strip()

    # 如果包含类似 -bm 1.0 这样的选项参数，我们尝试过滤掉以 '-' 开头的参数及其对应的值
    # 这里采用一种回退策略：直接取最后一个 token，绝大多数带参数的 MTL 生成器不会在文件名中加空格
    return parts[-1].strip()


def process_single_obj(obj_path: Path, source_dir: Path, target_dir: Path):
    """
    处理单个 OBJ 文件的完整生命周期：解析、追踪引用、复制
    """
    try:
        # 1. 以 OBJ 名称创建独立的子目录
        model_name = obj_path.stem
        dest_subdir = target_dir / model_name
        dest_subdir.mkdir(parents=True, exist_ok=True)

        # 使用集合去重，保存所有需要复制的文件绝对路径
        files_to_copy = {obj_path}
        mtl_names = []

        # 2. 解析 OBJ，提取引用的 MTL 文件（不依赖同名逻辑）
        # 使用 errors='ignore' 防止极少数包含非标准字符的文件导致解析崩溃
        with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.lower().startswith('mtllib '):
                    parts = line.split(maxsplit=1)
                    if len(parts) > 1:
                        mtl_names.append(parts[1].strip())

        # 3. 遍历提取到的 MTL 文件并解析贴图
        for mtl_name in mtl_names:
            mtl_path = source_dir / mtl_name

            if not mtl_path.exists():
                logging.warning(f"缺失 MTL 文件: {mtl_path.name} (被 {obj_path.name} 引用)")
                continue

            files_to_copy.add(mtl_path)

            with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
                while line := f.readline():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    keyword = line.split(maxsplit=1)[0].lower()
                    if keyword in TEXTURE_KEYWORDS:
                        tex_name = extract_texture_path(line)
                        # 处理有些引擎导出的绝对路径或包含反斜杠的路径
                        tex_name = tex_name.replace('\\', '/')
                        tex_path = source_dir / tex_name

                        if tex_path.exists():
                            files_to_copy.add(tex_path)
                        else:
                            logging.warning(f"缺失贴图文件: {tex_name} (被 {mtl_path.name} 引用)")

        # 4. 批量复制该模型关联的所有文件
        for src_file in files_to_copy:
            # 保持目标目录下的相对结构为空，所有文件摊平放在以 OBJ 命名的子目录中
            # 如果原始数据中贴图存在相对子目录结构，这里会自动展平。如需保留原有贴图相对路径，可修改此处
            dest_file = dest_subdir / src_file.name

            # 如果文件已存在且大小相同，则跳过（支持断点续传/增量复制）
            if dest_file.exists() and dest_file.stat().st_size == src_file.stat().st_size:
                continue

            shutil.copy2(src_file, dest_file)

        logging.info(f"成功处理: {obj_path.name} (共打包 {len(files_to_copy)} 个文件)")

    except Exception as e:
        logging.error(f"处理文件 {obj_path.name} 时发生异常: {str(e)}")


def main(source_dir: str, target_dir: str):
    src_path = Path(source_dir).resolve()
    tgt_path = Path(target_dir).resolve()

    if not src_path.is_dir():
        logging.error(f"源目录无效: {src_path}")
        return

    tgt_path.mkdir(parents=True, exist_ok=True)

    # 扫描目录下所有的 .obj 文件（当前层级）
    obj_files = list(src_path.glob('*.obj'))
    total_objs = len(obj_files)

    if total_objs == 0:
        logging.info("未在源目录发现 .obj 文件。")
        return

    logging.info(f"发现 {total_objs} 个 OBJ 文件，准备开始并发处理...")

    # 动态计算高并发线程数。
    # 针对纯 I/O 操作，突破 CPU 核心数限制，利用系统的异步 I/O 队列机制
    # 建议设置: NVMe SSD (CPU核心数*8), SATA SSD (核心数*4), 机械硬盘 HDD (核心数*2)
    max_threads = min(128, (os.cpu_count() or 4) * 8)

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="IOWorker") as executor:
        # 提交所有任务到线程池
        futures = {
            executor.submit(process_single_obj, obj_path, src_path, tgt_path): obj_path
            for obj_path in obj_files
        }

        # 进度追踪
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            if completed % 100 == 0 or completed == total_objs:
                logging.info(f"总体进度: {completed}/{total_objs} ({(completed / total_objs) * 100:.1f}%)")

    elapsed = time.time() - start_time
    logging.info(f"处理完成！总计 {total_objs} 个模型，耗时: {elapsed:.2f} 秒。")


if __name__ == '__main__':
    SOURCE_DIRECTORY = r"./source_models"
    TARGET_DIRECTORY = r"./packed_models"

    main(SOURCE_DIRECTORY, TARGET_DIRECTORY)