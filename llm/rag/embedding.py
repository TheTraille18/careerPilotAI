from langchain_aws import BedrockEmbeddings

from config import get_aws_region, get_embedding_model_id


def create_embeddings() -> BedrockEmbeddings:

    embedding = BedrockEmbeddings(
        model_id=get_embedding_model_id(),
        region_name=get_aws_region(),
    )

    return embedding