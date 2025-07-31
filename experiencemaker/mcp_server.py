import sys
from typing import List

from dotenv import load_dotenv
from fastmcp import FastMCP

from experiencemaker.service.experience_maker_service import ExperienceMakerService

load_dotenv()

mcp = FastMCP("ExperienceMaker")
service = ExperienceMakerService(sys.argv[1:])


@mcp.tool
def retriever(query: str,
              messages: List[dict] = None,
              top_k: int = 1,
              workspace_id: str = "default",
              config: dict = None) -> dict:
    """
    Retrieve experiences from the workspace based on a query.

    Args:
        query: Query string
        messages: List of messages
        top_k: Number of top experiences to retrieve
        workspace_id: Workspace identifier
        config: Additional configuration parameters

    Returns:
        Dictionary containing retrieved experiences
    """
    return service(api="retriever", request={
        "query": query,
        "messages": messages if messages else [],
        "top_k": top_k,
        "workspace_id": workspace_id,
        "config": config if config else {},
    }).model_dump()


@mcp.tool
def summarizer(traj_list: List[dict], workspace_id: str = "default", config: dict = None) -> dict:
    """
    Summarize trajectories into experiences.

    Args:
        traj_list: List of trajectories
        workspace_id: Workspace identifier
        config: Additional configuration parameters

    Returns:
        experiences
    """
    return service(api="summarizer", request={
        "traj_list": traj_list,
        "workspace_id": workspace_id,
        "config": config if config else {},
    }).model_dump()


@mcp.tool
def vector_store(action: str,
                 src_workspace_id: str = "",
                 workspace_id: str = "",
                 path: str = "./",
                 config: dict = None) -> dict:
    """
    Perform vector store operations.

    Args:
        action: Action to perform (e.g., "copy", "delete", "dump", "load")
        src_workspace_id: Source workspace identifier
        workspace_id: Workspace identifier
        path: Path to the vector store
        config: Additional configuration parameters

    Returns:
        Dictionary containing the result of the vector store operation
    """
    return service(api="vector_store", request={
        "action": action,
        "src_workspace_id": src_workspace_id,
        "workspace_id": workspace_id,
        "path": path,
        "config": config if config else {},
    }).model_dump()


def main():
    mcp_transport: str = service.init_app_config.mcp_transport
    if mcp_transport == "sse":
        mcp.run(transport="sse", host=service.http_service_config.host, port=service.http_service_config.port)
    elif mcp_transport == "stdio":
        mcp.run(transport="stdio")
    else:
        raise ValueError(f"Unsupported mcp transport: {mcp_transport}")


if __name__ == "__main__":
    main()


# start with:
# experiencemaker_mcp \
#   mcp_transport=stdio \
#   http_service.port=8001 \
#   llm.default.model_name=qwen3-32b \
#   embedding_model.default.model_name=text-embedding-v4 \
#   vector_store.default.backend=local_file