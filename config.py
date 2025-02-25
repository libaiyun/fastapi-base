import os
import shutil
import socket
import traceback
from enum import Enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

_pwd = Path(__file__).parent
CONFIG_FILE = _pwd / "config.yaml"
CACHE_CONFIG_FILE = _pwd / "cache_config.yaml"


# 获取本地 IP 地址
def get_local_ip(prefix: str = "") -> str | None:
    """
    # 多网卡情况下，根据前缀获取IP
    :param prefix: 192.168
    :return:
    """
    for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
        if ip.startswith(prefix):
            return ip


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class UvicornConfig(BaseModel):
    workers: int
    limit_concurrency: int
    limit_max_requests: int


class LogConfig(BaseModel):
    app_logfile: str
    server_logfile: str
    access_logfile: str
    scheduler_async_logfile: str
    scheduler_logfile: str
    task_logfile: str
    rotate_when: Literal["S", "M", "H", "D", "MIDNIGHT", "W"]
    backup_count: int

    @field_validator(
        "app_logfile",
        "server_logfile",
        "access_logfile",
        "scheduler_async_logfile",
        "scheduler_logfile",
        "task_logfile",
        mode="before",
    )
    def ensure_log_path_exists(cls, v):
        """确保日志目录存在"""
        os.makedirs(os.path.dirname(v), exist_ok=True)
        return v


class MySQLConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str


class DBConfig(BaseModel):
    echo: bool
    pool_size: int
    max_overflow: int
    slow_query_threshold: float


class GatewayConfig(BaseModel):
    login_url: str
    service_url: str


class NacosConfig(BaseModel):
    server_url: str
    auth_enabled: bool
    username: str
    password: str
    namespace_id: str
    group: str
    enable_service_register: bool
    enable_config_sync: bool


class RedisConfig(BaseModel):
    url: str
    db: int


class ESConfig(BaseModel):
    host: str
    user: str
    password: str
    timeout: int


class SentryConfig(BaseModel):
    enabled: bool
    dsn: str
    traces_sample_rate: float
    profiles_sample_rate: float


class AppConfig(BaseModel):
    service_name: str
    host: str = Field(default_factory=lambda: get_local_ip("192.168"))
    port: int
    environment: Environment
    enable_auth: bool

    uvicorn: UvicornConfig
    log: LogConfig
    mysql: MySQLConfig
    db: DBConfig
    gateway: GatewayConfig
    nacos: NacosConfig
    redis: RedisConfig
    es: ESConfig
    sentry: SentryConfig

    @model_validator(mode="after")
    def format_service_name(self) -> Self:
        if self.environment != Environment.PRODUCTION:
            self.service_name = f"{self.service_name}-{self.environment}"
        service_name = self.service_name.replace("_", "-")  # nacos服务地址不允许下划线
        self.gateway.service_url = self.gateway.service_url.replace("{service_name}", service_name)
        return self

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> "AppConfig":
        with open(file_path, "r", encoding="utf8") as f:
            data = yaml.safe_load(f)
            return AppConfig.model_validate(data)

    def to_yaml(self, file_path: str | Path):
        with open(file_path, "w", encoding="utf8") as f:
            yaml.dump(self.model_dump(mode="json"), f)


def load_config(cache_config_file: str | Path) -> AppConfig:
    """加载缓存配置或默认配置"""
    if os.path.exists(cache_config_file):
        print("加载缓存配置...")
        try:
            return AppConfig.from_yaml(cache_config_file)
        except Exception as e:
            print(f"缓存配置加载失败，启用默认配置。错误信息：{e}，异常堆栈：\n{traceback.format_exc()}")
            return AppConfig.from_yaml(CONFIG_FILE)
    else:
        print("缓存配置不存在，启用默认配置...")
        default_config = AppConfig.from_yaml(CONFIG_FILE)
        shutil.copy(CONFIG_FILE, cache_config_file)  # 缓存默认配置
        return default_config


config = load_config(CACHE_CONFIG_FILE)
