import os
from enum import Enum
from pathlib import Path
from typing import Optional, Literal

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource


class AppEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"
    TEST = "test"


def get_app_env() -> AppEnv:
    env_value = os.getenv("APP_ENV", "dev").lower()
    return AppEnv(env_value)


APP_ENV = get_app_env()


class ServerConfig(BaseModel):
    host: str
    port: int
    workers: int = 1
    limit_concurrency: int = 200
    limit_max_requests: Optional[int] = None


class LogConfig(BaseModel):
    app_logfile: str = "log/app.log"
    server_logfile: str = "log/server.log"
    access_logfile: str = "log/access.log"
    task_logfile: str = "log/task.log"
    rotate_when: Literal["S", "M", "H", "D", "MIDNIGHT", "W"] = "MIDNIGHT"
    backup_count: int = 30

    @field_validator("app_logfile", "server_logfile", "access_logfile", "task_logfile", mode="before")
    def ensure_log_path_exists(cls, v):
        Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v


class MySQLConfig(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str


class DBConfig(BaseModel):
    echo: bool = False
    pool_size: int = 64
    max_overflow: int = 128
    slow_query_threshold: float = 2.0


class NacosConfig(BaseModel):
    server_url: str
    auth_enabled: bool = False
    username: str = ""
    password: str = ""
    namespace_id: str = "public"
    group: str = "DEFAULT_GROUP"
    enable_service_register: bool = False
    enable_config_sync: bool = False
    sync_interval: int = 15


class GatewayConfig(BaseModel):
    login_url: str
    service_url: str


class RedisConfig(BaseModel):
    url: str
    db: int = 1


class ESConfig(BaseModel):
    host: str
    user: str
    password: str
    timeout: int = 60


class SentryConfig(BaseModel):
    enabled: bool = False
    dsn: str
    traces_sample_rate: float = 1.0
    profiles_sample_rate: float = 0.05


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="_",  # 嵌套模型环境变量分隔符，如MYSQL_HOST
        # env_file=(".env", f".env.{APP_ENV}"),
        yaml_file=("config-default.yaml", f"config-{APP_ENV}.yaml"),
        yaml_file_encoding="utf-8",
        case_sensitive=False,  # 大小写不敏感
        nested_model_default_partial_update=True,  # 允许嵌套模型部分更新
    )

    project_name: str
    enable_auth: bool = False

    server: ServerConfig
    log: LogConfig
    mysql: MySQLConfig
    db: DBConfig
    nacos: NacosConfig
    gateway: GatewayConfig
    redis: RedisConfig
    es: ESConfig
    sentry: SentryConfig

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @property
    def namespace(self):
        return f"{self.project_name}-{APP_ENV}"

    @property
    def service_name(self):
        return self.namespace.replace("_", "-")

    @model_validator(mode="after")
    def format_service_url(self) -> "AppConfig":
        self.gateway.service_url = self.gateway.service_url.replace("{service_name}", self.service_name)
        return self
