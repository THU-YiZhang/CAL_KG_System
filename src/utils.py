"""
工具函数模块
提供通用的工具函数和配置加载功能
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import threading
from openai import OpenAI

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._api_config = None
        self._prompts = None
    
    def load_api_config(self) -> Dict[str, Any]:
        """加载API配置"""
        if self._api_config is None:
            config_path = self.config_dir / "api_config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._api_config = json.load(f)
        return self._api_config
    
    def load_prompts(self) -> Dict[str, Any]:
        """加载提示词配置"""
        if self._prompts is None:
            prompts_path = self.config_dir / "prompts.json"
            with open(prompts_path, 'r', encoding='utf-8') as f:
                self._prompts = json.load(f)
        return self._prompts
    
    def get_api_client(self) -> OpenAI:
        """获取API客户端"""
        config = self.load_api_config()
        api_settings = config["api_settings"]
        
        return OpenAI(
            api_key=api_settings["api_key"],
            base_url=api_settings["base_url"]
        )
    
    def get_model_config(self, module_name: str) -> Dict[str, Any]:
        """获取特定模块的模型配置"""
        config = self.load_api_config()
        base_config = config["api_settings"]
        
        # 如果有模块特定配置，则合并
        if module_name in config.get("model_specific", {}):
            module_config = config["model_specific"][module_name]
            return {**base_config, **module_config}
        
        return base_config

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_tasks: int, task_name: str = "Processing"):
        self.total_tasks = total_tasks
        self.task_name = task_name
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update(self, completed: int = 1, failed: int = 0):
        """更新进度"""
        with self.lock:
            self.completed_tasks += completed
            self.failed_tasks += failed
            self._print_progress()
    
    def _print_progress(self):
        """打印进度信息"""
        total_processed = self.completed_tasks + self.failed_tasks
        if total_processed == 0:
            return
        
        elapsed = time.time() - self.start_time
        progress = (total_processed / self.total_tasks) * 100
        speed = total_processed / elapsed if elapsed > 0 else 0
        
        if total_processed < self.total_tasks:
            eta = (elapsed / total_processed) * (self.total_tasks - total_processed)
            print(f"📊 {self.task_name}: {total_processed}/{self.total_tasks} "
                  f"({progress:.1f}%) - 速度: {speed:.1f}/秒 - 预计剩余: {eta:.1f}秒")
        else:
            print(f"✅ {self.task_name}完成: {self.completed_tasks}成功, "
                  f"{self.failed_tasks}失败, 总耗时: {elapsed:.1f}秒")

class FileManager:
    """文件管理器"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            "data/input",
            "output/intermediate/sections",
            "output/intermediate/main_logic", 
            "output/intermediate/sub_logic",
            "output/intermediate/connections",
            "output/final",
            "logs"
        ]
        
        for dir_path in directories:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, category: str, filename: str = "") -> Path:
        """获取文件路径"""
        path_mapping = {
            "input": "data/input",
            "sections": "output/intermediate/sections",
            "main_logic": "output/intermediate/main_logic",
            "sub_logic": "output/intermediate/sub_logic", 
            "connections": "output/intermediate/connections",
            "final": "output/final",
            "logs": "logs"
        }
        
        if category not in path_mapping:
            raise ValueError(f"Unknown category: {category}")
        
        base_path = self.base_dir / path_mapping[category]
        
        if filename:
            return base_path / filename
        return base_path
    
    def save_json(self, data: Dict[str, Any], category: str, filename: str):
        """保存JSON数据"""
        file_path = self.get_path(category, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存文件: {file_path}")
    
    def load_json(self, category: str, filename: str) -> Dict[str, Any]:
        """加载JSON数据"""
        file_path = self.get_path(category, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

class Logger:
    """日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置日志
        log_file = self.log_dir / f"cal_kg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('CAL_KG')
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)

def format_time_duration(seconds: float) -> str:
    """格式化时间持续时间"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"

def safe_filename(text: str) -> str:
    """生成安全的文件名"""
    import re
    # 移除或替换不安全的字符
    safe_text = re.sub(r'[^\w\-_.]', '_', text)
    # 限制长度
    return safe_text[:100]

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"⚠️ 尝试 {attempt + 1} 失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# 全局实例
config_manager = ConfigManager()
file_manager = FileManager()
logger = Logger()
