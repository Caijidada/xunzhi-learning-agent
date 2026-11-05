from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    timeout: float = 90

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        directory = Path(os.getenv("STUDY_DATA_DIR", str(ROOT / "data")))
        if not directory.is_absolute():
            directory = ROOT / directory
        return cls(directory, os.getenv("LLM_API_KEY", ""),
                   os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
                   os.getenv("LLM_MODEL", "deepseek-flash"), float(os.getenv("LLM_TIMEOUT", "90")))
