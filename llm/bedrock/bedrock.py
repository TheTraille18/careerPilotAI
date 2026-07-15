from langchain_aws import ChatBedrockConverse

from config import get_aws_region, get_bedrock_model_id


def llm_service() -> ChatBedrockConverse:

    llm = ChatBedrockConverse(
        model=get_bedrock_model_id(),
        region_name=get_aws_region(),
        temperature=0,
        max_tokens=4000,
    )

    return llm