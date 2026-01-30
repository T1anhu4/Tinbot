import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 主 Agent 配置 (对应 FastGPT)
    API_URL: str
    API_KEY: str
    MODEL_NAME: str

    # 视觉模型配置 (对应 .env 中的 VISION_MODEL_xxx)
    # 给定默认值以防 .env 缺失
    VISION_MODEL_NAME: str = "qwen-vl-max"
    VISION_MODEL_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VISION_MODEL_API_KEY: str = "" # 必填，如果 .env 里没有就会报错

    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()