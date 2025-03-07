from config.models import APP_ENV, AppConfig
from config.nacos_sync import ConfigSyncer

config = AppConfig()

config_syncer = ConfigSyncer(config)

__all__ = ["APP_ENV", "config", "config_syncer"]
