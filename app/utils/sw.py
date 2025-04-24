from app.config import config
from skywalking import agent, config as sw_config

from app.constants import SW_AGENT_DISABLE_PLUGINS


def start_sw_agent():
    if not config.sw.enabled:
        return
    sw_config.init(
        agent_collector_backend_services=config.sw.agent_collector_backend_services,
        agent_name=config.service_name,
        agent_log_reporter_active=config.sw.agent_log_reporter_active,
        agent_log_reporter_level=config.sw.agent_log_reporter_level,
        agent_meter_reporter_active=config.sw.agent_meter_reporter_active,
        agent_disable_plugins=SW_AGENT_DISABLE_PLUGINS,
    )
    agent.start()
