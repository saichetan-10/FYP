"""Configuration and environment setup."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration."""

    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    database: str = os.getenv("DB_NAME", "semantic_grounding")

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ChromaConfig:
    """ChromaDB vector store configuration."""

    persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    collection_name: str = "business_rules"


@dataclass
class OntologyConfig:
    """Business ontology configuration."""

    entities_file: str = os.getenv("ONTOLOGY_ENTITIES", "./data/ontology/entities.json")
    metrics_file: str = os.getenv("ONTOLOGY_METRICS", "./data/ontology/metrics.json")
    rules_file: str = os.getenv("ONTOLOGY_RULES", "./data/ontology/rules.json")


@dataclass
class DriftMetricConfig:
    """Semantic drift metric configuration."""

    intent_alignment_weight: float = 0.4
    constraint_adherence_weight: float = 0.3
    result_plausibility_weight: float = 0.3
    drift_threshold: float = 0.15  # Target drift must be below this
    z_score_threshold: float = 3.0  # Outlier detection threshold


@dataclass
class LoggingConfig:
    """Structured logging configuration."""

    log_dir: str = os.getenv("LOG_DIR", "./logs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    json_logs: bool = True
    log_file: str = "app.log"

    @property
    def log_path(self) -> str:
        """Get full log file path."""
        os.makedirs(self.log_dir, exist_ok=True)
        return os.path.join(self.log_dir, self.log_file)


@dataclass
class APIConfig:
    """FastAPI configuration."""

    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    workers: int = int(os.getenv("API_WORKERS", "4"))
    reload: bool = os.getenv("API_RELOAD", "false").lower() == "true"


@dataclass
class SystemConfig:
    """Main system configuration."""

    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    chroma: ChromaConfig = field(default_factory=ChromaConfig)
    ontology: OntologyConfig = field(default_factory=OntologyConfig)
    drift_metric: DriftMetricConfig = field(default_factory=DriftMetricConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    eval_mode: bool = False
    db_dialect: str = os.getenv("DB_DIALECT", "postgresql")


# Global config instance
config = SystemConfig()
