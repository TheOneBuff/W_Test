import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
LOG_DIR = "/data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 全局标志，确保 setup_logging 只执行一次
_logging_initialized = False

def setup_logging():
    """
    配置日志记录器
    确保所有进程（包括 Celery 工作进程）使用统一的日志配置
    """
    global _logging_initialized
    
    # 如果已经初始化过，跳过重复配置
    if _logging_initialized:
        return logging.getLogger()
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除现有的处理器
    for handler in logger.handlers[:]:  # 使用切片复制避免迭代时修改
        logger.removeHandler(handler)

    # 配置文件日志处理器
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=3,  # 保留3个备份
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # 配置控制台日志处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # 添加处理器到根日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 禁用日志传播，避免重复日志
    logger.propagate = False

    # 为特定模块配置日志
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)

    # 确保 Celery 任务使用我们的日志配置
    for logger_name in ["celery", "celery.task", "celery.worker"]:
        celery_logger = logging.getLogger(logger_name)
        celery_logger.setLevel(logging.INFO)
        # 清除 Celery 默认的处理器
        for handler in celery_logger.handlers[:]:  # 使用切片复制避免迭代时修改
            celery_logger.removeHandler(handler)
        # 添加我们的处理器
        celery_logger.addHandler(file_handler)
        celery_logger.addHandler(console_handler)
        # 禁用传播
        celery_logger.propagate = False

    # 标记为已初始化
    _logging_initialized = True
    
    return logger

# 导出配置好的日志记录器
app_logger = setup_logging()