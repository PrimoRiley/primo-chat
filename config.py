import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Config:
    """Configuration management for multi-tenant RAG system."""
    
    def __init__(self):
        # Core OpenAI Configuration
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        
        # Organization Configuration
        self.organization_name: str = os.getenv("ORGANIZATION_NAME", "default")
        self.organization_display_name: str = os.getenv("ORGANIZATION_DISPLAY_NAME", self.organization_name.replace("-", " ").title())
        
        # GCP Configuration
        self.gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
        self.gcp_region: str = os.getenv("GCP_REGION", "us-central1")
        
        # Chainlit Configuration
        self.chainlit_host: str = os.getenv("CHAINLIT_HOST", "0.0.0.0")
        self.chainlit_port: int = int(os.getenv("CHAINLIT_PORT", "8000"))
        
        # Database Configuration
        self.data_directory: str = os.getenv("DATA_DIRECTORY", "/data")
        
        # OpenAI Model Configuration
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.openai_assistant_model: str = os.getenv("OPENAI_ASSISTANT_MODEL", "gpt-4-turbo-preview")
        
        # Vector Store Configuration
        self.vector_store_name: str = f"{self.organization_name}-knowledge-base"
        self.vector_store_expires_days: int = int(os.getenv("VECTOR_STORE_EXPIRES_DAYS", "365"))
        
        # File Upload Configuration
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
        self.allowed_file_types: list = os.getenv(
            "ALLOWED_FILE_TYPES", 
            "pdf,txt,md,docx,doc,rtf,html,json,csv,xml"
        ).split(",")
        
        # Chat Configuration
        self.max_chat_history: int = int(os.getenv("MAX_CHAT_HISTORY", "50"))
        self.chat_title_length: int = int(os.getenv("CHAT_TITLE_LENGTH", "50"))
        
        # Authentication Configuration (optional)
        self.require_auth: bool = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
        self.oauth_provider: str = os.getenv("OAUTH_PROVIDER", "google")
        
        # Feature Flags
        self.enable_document_management: bool = os.getenv("ENABLE_DOCUMENT_MANAGEMENT", "true").lower() == "true"
        self.enable_chat_history: bool = os.getenv("ENABLE_CHAT_HISTORY", "true").lower() == "true"
        self.enable_user_management: bool = os.getenv("ENABLE_USER_MANAGEMENT", "false").lower() == "true"
        
        # Development/Debug Configuration
        self.debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Set log level
        logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))
        
        # Validate critical configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate critical configuration values."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.organization_name:
            errors.append("ORGANIZATION_NAME is required")
        
        if self.max_file_size_mb <= 0:
            errors.append("MAX_FILE_SIZE_MB must be positive")
        
        if self.max_file_size_mb > 512:  # OpenAI limit
            errors.append("MAX_FILE_SIZE_MB cannot exceed 512MB (OpenAI limit)")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    @property
    def is_configured(self) -> bool:
        """Check if minimum configuration is available."""
        return bool(self.openai_api_key and self.organization_name)
    
    @property
    def database_path(self) -> str:
        """Get the SQLite database path for this organization."""
        return f"{self.data_directory}/{self.organization_name}.db"
    
    @property
    def assistant_instructions(self) -> str:
        """Get the assistant instructions for this organization."""
        return f"""You are a helpful AI assistant for {self.organization_display_name}. 

You have access to a knowledge base containing documents uploaded by users. When answering questions:

1. Search through the uploaded documents first to find relevant information
2. Always cite your sources when referencing specific documents
3. If you can't find the answer in the documents, clearly state that and provide general knowledge
4. Be concise but thorough in your responses
5. Ask clarifying questions when the user's request is ambiguous

Current knowledge base contains documents that users have uploaded. Use the file_search tool to find relevant information."""
    
    def get_environment_info(self) -> dict:
        """Get current environment information for debugging."""
        return {
            "organization_name": self.organization_name,
            "organization_display_name": self.organization_display_name,
            "openai_model": self.openai_model,
            "vector_store_name": self.vector_store_name,
            "max_file_size_mb": self.max_file_size_mb,
            "allowed_file_types": self.allowed_file_types,
            "features": {
                "document_management": self.enable_document_management,
                "chat_history": self.enable_chat_history,
                "user_management": self.enable_user_management,
                "auth_required": self.require_auth
            },
            "debug_mode": self.debug_mode,
            "data_directory": self.data_directory
        }
    
    def to_dict(self) -> dict:
        """Convert config to dictionary (for debugging/logging)."""
        return {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_') and key != 'openai_api_key'  # Don't expose API key
        }

# Global config instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config

def validate_file_upload(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate file upload against configuration."""
    # Check file size
    max_size_bytes = config.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({config.max_file_size_mb}MB)"
    
    # Check file type
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    if file_extension not in config.allowed_file_types:
        return False, f"File type '{file_extension}' not allowed. Supported types: {', '.join(config.allowed_file_types)}"
    
    return True, "File is valid"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.1f} GB"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."