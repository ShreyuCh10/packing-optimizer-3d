import os
from dotenv import find_dotenv, load_dotenv
from langchain_openai import AzureChatOpenAI

# Automatically load environment variables from nearest .env file
load_dotenv(find_dotenv(), override=False)

deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
model_name = os.environ.get("AZURE_OPENAI_MODEL_NAME") or deployment

llm = AzureChatOpenAI(
    azure_deployment=deployment,
    model_name=model_name,
    openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "https://placeholder.openai.azure.com"),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY", "placeholder"),
    temperature=float(os.environ.get("AZURE_OPENAI_TEMPERATURE", 0.0)),
)
