import os
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
    model_name=os.environ.get("AZURE_OPENAI_MODEL_NAME", "gpt-4o"),
    openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "https://placeholder.openai.azure.com"),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY", "placeholder"),
)
