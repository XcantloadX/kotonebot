from pydantic import BaseModel, Field


class AiConfig(BaseModel):
    provider_type: str = Field(default="openai", alias="providerType")
    endpoint: str = ""
    model: str = ""
    api_key: str = Field(default="", alias="apiKey")

    model_config = {"populate_by_name": True}
