"""Configuration management for the AWS Strands Monitoring Agent."""

import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dataclasses import dataclass


class AgentConfig(BaseSettings):
    """Main configuration for the monitoring agent."""
    
    # Kubernetes configuration
    kubernetes_config: str = Field(default="kubeconfig", description="Kubernetes config type")
    kubeconfig_path: Optional[str] = Field(default=None, description="Path to kubeconfig file")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    # Data collection limits
    max_events: int = Field(default=100, description="Maximum events to collect")
    max_log_lines: int = Field(default=100, description="Maximum log lines per pod")
    analysis_timeout: int = Field(default=30, description="Analysis timeout in seconds")
    
    # HTTP server configuration
    host: str = Field(default="0.0.0.0", description="HTTP server host")
    port: int = Field(default=8080, description="HTTP server port")
    
    # AWS Strands configuration
    strands_region: str = Field(default="us-east-1", description="AWS region for Strands")
    strands_endpoint: Optional[str] = Field(default=None, description="Custom Strands endpoint")
    strands_model: str = Field(default="anthropic.claude-3-5-sonnet-20240620-v1:0", description="Claude-3-Sonnet model for analysis")
    strands_session_ttl: int = Field(default=3600, description="State session TTL in seconds")
    strands_timeout: int = Field(default=30, description="Strands execution timeout in seconds")
    strands_max_retries: int = Field(default=3, description="Maximum retries for Strands operations")
    strands_temperature: float = Field(default=0.1, description="Model temperature for consistent analysis")
    strands_max_tokens: int = Field(default=8000, description="Maximum tokens for Strands responses")
    strands_disable_streaming: bool = Field(default=True, description="Disable streaming mode for Bedrock compatibility - ALWAYS TRUE")
    strands_fallback_model: str = Field(default="anthropic.claude-3-haiku-20240307-v1:0", description="Fallback model for streaming issues")
    strands_rate_limit_interval: float = Field(default=2.0, description="Minimum seconds between requests to prevent throttling")
    
    # AWS Bedrock configuration for Strands
    bedrock_region: str = Field(default="us-east-1", description="AWS Bedrock region")
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20240620-v1:0", description="Bedrock model ID")
    bedrock_endpoint_url: Optional[str] = Field(default=None, description="Custom Bedrock endpoint URL")
    
    # AWS credentials configuration
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    aws_session_token: Optional[str] = Field(default=None, description="AWS Session Token")
    aws_profile: Optional[str] = Field(default=None, description="AWS Profile name")
    
    # Auto-monitoring configuration
    auto_monitoring_enabled: bool = Field(default=True, description="Enable auto-monitoring")
    event_batch_size: int = Field(default=10, description="Event batch size for auto-analysis")
    event_batch_timeout: int = Field(default=30, description="Event batch timeout in seconds")
    monitored_namespaces: Optional[str] = Field(default=None, description="Comma-separated list of namespaces to monitor")
    critical_event_types: str = Field(default="Warning,Error", description="Comma-separated list of critical event types")
    analysis_retention_days: int = Field(default=30, description="Analysis retention period in days")
    max_concurrent_analyses: int = Field(default=3, description="Maximum concurrent analyses")
    deduplication_window: int = Field(default=300, description="Event deduplication window in seconds")
    
    # Error handling and fallback configuration
    enable_error_handling: bool = Field(default=True, description="Enable comprehensive error handling")
    enable_fallback_analysis: bool = Field(default=True, description="Enable rule-based fallback analysis")
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts for failed operations")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout: int = Field(default=60, description="Circuit breaker recovery timeout in seconds")
    error_history_size: int = Field(default=1000, description="Maximum number of errors to keep in history")
    fallback_confidence_threshold: float = Field(default=0.5, description="Minimum confidence threshold for fallback analysis")
    
    # Performance optimization configuration
    enable_performance_optimization: bool = Field(default=True, description="Enable performance optimization features")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    max_concurrent_requests: int = Field(default=3, description="Maximum concurrent requests")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    memory_warning_mb: int = Field(default=800, description="Memory warning threshold in MB")
    memory_critical_mb: int = Field(default=1000, description="Memory critical threshold in MB")
    enable_prompt_optimization: bool = Field(default=True, description="Enable AI prompt optimization")
    enable_request_queuing: bool = Field(default=True, description="Enable intelligent request queuing")
    enable_memory_monitoring: bool = Field(default=True, description="Enable memory usage monitoring")
    cache_cluster_data_ttl: int = Field(default=60, description="Cluster data cache TTL in seconds")
    cache_analysis_results_ttl: int = Field(default=300, description="Analysis results cache TTL in seconds")
    
    class Config:
        env_prefix = "AGENT_"
        case_sensitive = False


@dataclass
class StrandsConfig:
    """Configuration for AWS Strands integration."""
    region: str = "us-east-1"
    endpoint: Optional[str] = None
    model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    session_ttl: int = 3600
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.1
    max_tokens: int = 4000
    
    # AWS credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_profile: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "StrandsConfig":
        """Create configuration from environment variables."""
        return cls(
            region=os.getenv("STRANDS_REGION", "us-east-1"),
            endpoint=os.getenv("STRANDS_ENDPOINT"),
            model=os.getenv("STRANDS_MODEL", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
            session_ttl=int(os.getenv("STRANDS_SESSION_TTL", "3600")),
            timeout=int(os.getenv("STRANDS_TIMEOUT", "30")),
            max_retries=int(os.getenv("STRANDS_MAX_RETRIES", "3")),
            temperature=float(os.getenv("STRANDS_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("STRANDS_MAX_TOKENS", "4000")),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            aws_profile=os.getenv("AWS_PROFILE")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent initialization."""
        return {
            "region": self.region,
            "endpoint": self.endpoint,
            "model": self.model,
            "session_ttl": self.session_ttl,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


def load_config() -> AgentConfig:
    """Load configuration from environment variables and defaults."""
    return AgentConfig()

def get_config() -> AgentConfig:
    """Alias for load_config for backward compatibility."""
    return load_config()


def validate_config(config: AgentConfig) -> None:
    """Validate configuration values."""
    if config.analysis_timeout <= 0:
        raise ValueError("Analysis timeout must be positive")
    
    if config.max_events <= 0:
        raise ValueError("Max events must be positive")
    
    if config.max_log_lines <= 0:
        raise ValueError("Max log lines must be positive")
    
    if config.port <= 0 or config.port > 65535:
        raise ValueError("Port must be between 1 and 65535")


class AWSConfig:
    """AWS configuration helper."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
    
    def get_strands_config(self) -> Dict[str, Any]:
        """Get Strands configuration dictionary."""
        return {
            "region": self.config.strands_region,
            "model": self.config.strands_model,
            "fallback_model": self.config.strands_fallback_model,
            "disable_streaming": self.config.strands_disable_streaming,
            "session_ttl": self.config.strands_session_ttl,
            "timeout": self.config.strands_timeout,
            "max_retries": self.config.strands_max_retries,
            "temperature": self.config.strands_temperature,
            "max_tokens": self.config.strands_max_tokens,
            "aws_access_key_id": self.config.aws_access_key_id,
            "aws_secret_access_key": self.config.aws_secret_access_key,
            "aws_session_token": self.config.aws_session_token,
            "aws_profile": self.config.aws_profile
        }


def get_config() -> AgentConfig:
    """Get validated configuration."""
    config = load_config()
    validate_config(config)
    return config