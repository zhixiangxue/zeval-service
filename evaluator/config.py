"""评估器配置"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvaluatorConfig:
    """Mortgage RAG 评估器配置
    
    Example:
        # 从环境变量创建
        config = EvaluatorConfig.from_env()
        
        # 自定义配置
        config = EvaluatorConfig(
            llm_uri="openai/gpt-4o-mini",
            api_key="sk-xxx",
            num_test_cases=100
        )
    """
    
    # 必需配置
    llm_uri: str
    api_key: str
    
    # 可选配置
    max_concurrency: int = 3
    num_personas: int = 3
    num_test_cases: int = 50
    max_units: int = 50
    
    # RAG 系统配置
    rag_base_url: str = field(default_factory=lambda: os.getenv("RAG_BASE_URL", "http://13.56.109.233:8000"))
    rag_dataset_id: str = field(default_factory=lambda: os.getenv("RAG_DATASET_ID", "mortgage_guidelines"))
    rag_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "5")))
    
    # Mortgage 领域配置
    domain: str = "US residential real estate and home buying process"
    
    @classmethod
    def from_env(cls, llm_uri: str = "openai/gpt-4o-mini") -> "EvaluatorConfig":
        """从环境变量创建配置
        
        Args:
            llm_uri: LLM URI，格式: "{provider}/{model}"
                     例如: "openai/gpt-4o-mini", "openai/gpt-4o"
        
        支持的 provider:
            - openai: 使用 OPENAI_API_KEY
            - anthropic: 使用 ANTHROPIC_API_KEY
        """
        # 解析 URI
        if "/" not in llm_uri:
            raise ValueError(f"无效的 llm_uri 格式: {llm_uri}，必须是 'provider/model' 格式")
        
        provider = llm_uri.split("/")[0].lower()
        
        # 根据 provider 找对应的 API Key
        key_mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        
        if provider not in key_mapping:
            raise ValueError(
                f"不支持的 provider: {provider}\n"
                f"支持的 providers: {', '.join(key_mapping.keys())}"
            )
        
        env_key = key_mapping[provider]
        api_key = os.getenv(env_key)
        
        if not api_key:
            raise ValueError(f"{env_key} not found in environment")
        
        return cls(
            llm_uri=llm_uri,
            api_key=api_key
        )
