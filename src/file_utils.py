import os
import json
from typing import List, Dict
import logging

class FileUtils:
    """文件工具类
    
    处理文件扫描、读写等操作
    """
    
    @staticmethod
    def scan_python_files(folder_path: str) -> List[str]:
        """扫描目录下的所有 Python 文件
        
        Args:
            folder_path: 要扫描的文件夹路径
            
        Returns:
            List[str]: Python 文件路径列表
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"文件夹不存在: {folder_path}")
            
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"路径不是文件夹: {folder_path}")
            
        python_files = []
        
        # 遍历文件夹
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.py'):
                    # 忽略 __init__.py 和测试文件
                    if file != '__init__.py' and not file.startswith('test_'):
                        full_path = os.path.join(root, file)
                        python_files.append(full_path)
                        
        return python_files

    @staticmethod
    def save_json(data: dict, file_path: str):
        """保存 JSON 文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
        """
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            raise Exception(f"保存 JSON 文件失败: {str(e)}")

    @staticmethod
    def load_json(file_path: str) -> Dict:
        """加载 JSON 文件
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            Dict: 加载的数据
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 格式错误: {str(e)}")
        except Exception as e:
            raise IOError(f"读取 JSON 文件失败: {str(e)}")

    @staticmethod
    def merge_json_files(file_paths: List[str], output_file: str) -> None:
        """合并多个 JSON 文件
        
        Args:
            file_paths: JSON 文件路径列表
            output_file: 输出文件路径
        """
        merged_data = {}
        
        for file_path in file_paths:
            try:
                data = FileUtils.load_json(file_path)
                merged_data.update(data)
            except Exception as e:
                logging.warning(f"合并文件 {file_path} 时出错: {str(e)}")
                continue
                
        FileUtils.save_json(merged_data, output_file)

    @staticmethod
    def create_backup(file_path: str) -> str:
        """创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            str: 备份文件路径
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        backup_path = file_path + '.bak'
        counter = 1
        
        # 如果备份文件已存在,添加数字后缀
        while os.path.exists(backup_path):
            backup_path = f"{file_path}.bak{counter}"
            counter += 1
            
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            raise IOError(f"创建备份失败: {str(e)}")

    @staticmethod
    def is_file_empty(file_path: str) -> bool:
        """检查文件是否为空
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否为空
        """
        return os.path.exists(file_path) and os.path.getsize(file_path) == 0

    @staticmethod
    def get_file_info(file_path: str) -> Dict:
        """获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'accessed': stat.st_atime
        }

    @staticmethod
    def ensure_dir(dir_path: str) -> None:
        """确保目录存在,不存在则创建
        
        Args:
            dir_path: 目录路径
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    @staticmethod
    def init_output_dirs(base_path: str) -> dict:
        """初始化输出目录结构
        
        Args:
            base_path: 程序根目录
            
        Returns:
            dict: 包含各个输出目录路径的字典
        """
        # 创建主输出目录
        output_dir = os.path.join(base_path, "output")
        
        # 创建子目录
        dirs = {
            "main": output_dir,
            "temp": os.path.join(output_dir, "temp"),  # 临时文件
            "translations": os.path.join(output_dir, "translations"),  # 翻译结果
            "logs": os.path.join(output_dir, "logs"),  # 日志文件
            "debug": os.path.join(output_dir, "debug"),  # 调试信息
            "backups": os.path.join(output_dir, "backups"),  # 备份文件
        }
        
        # 创建所有目录
        for dir_path in dirs.values():
            os.makedirs(dir_path, exist_ok=True)
            
        return dirs

    @staticmethod
    def get_plugin_output_dir(base_path: str, plugin_path: str) -> dict:
        """获取插件对应的输出目录结构
        
        Args:
            base_path: 软件根目录
            plugin_path: 插件目录路径
            
        Returns:
            dict: 包含各个输出目录路径的字典
        """
        # 获取插件文件夹名称
        plugin_name = os.path.basename(plugin_path.rstrip(os.path.sep))
        
        # 创建主输出目录
        plugin_output_dir = os.path.join(base_path, "output", plugin_name)
        
        # 创建子目录
        dirs = {
            "main": plugin_output_dir,
            "temp": os.path.join(plugin_output_dir, "temp"),  # 临时文件
            "translations": os.path.join(plugin_output_dir, "translations"),  # 翻译结果
            "logs": os.path.join(plugin_output_dir, "logs"),  # 日志文件
            "debug": os.path.join(plugin_output_dir, "debug"),  # 调试信息
        }
        
        # 创建所有目录
        for dir_path in dirs.values():
            os.makedirs(dir_path, exist_ok=True)
            
        return dirs 