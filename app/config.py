from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    owner_chat_id: int

    vps1_public_ip: str

    vps2_host: str
    vps2_user: str = "checker"
    vps2_ssh_key_path: str | None = None
    vps2_remote_checker_path: str = "/home/checker/checker.py"

    check_interval_hours: int = 1

    state_path: str = "/workspace/data/proxies.json"
    mtproto_secrets_dir: str = "/workspace/data/mtproto"
    compose_file: str = "/workspace/docker-compose.yml"
    compose_project_dir: str = "/workspace"

