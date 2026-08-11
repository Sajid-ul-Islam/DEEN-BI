from __future__ import annotations

import base64
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


def _bootstrap_from_streamlit_secrets() -> None:
    """One-time bootstrap: read GCS config from st.secrets if env vars not already set.

    This lets Streamlit Cloud use the same gcp_service_account block from
    secrets.toml that GA4 uses, without any extra environment variable config.

    Secrets read (all optional):
        GCS_BUCKET_NAME          — e.g. "deen-bi-cache"  → sets PERSISTENT_CACHE_URI
        PERSISTENT_CACHE_URI     — full gs:// URI (overrides GCS_BUCKET_NAME)
        PERSISTENT_CACHE_NAMESPACE — sub-folder, defaults to "shared"
        [gcp_service_account]    — service account dict used as GCS token
    """
    try:
        import streamlit as st
        if not (hasattr(st, "secrets") and st.secrets):
            return
        sec = dict(st.secrets)
    except Exception:
        return

    # 1. Set PERSISTENT_CACHE_URI from secrets if not already in env
    if not os.environ.get("PERSISTENT_CACHE_URI"):
        uri = sec.get("PERSISTENT_CACHE_URI") or ""
        if not uri:
            bucket = sec.get("GCS_BUCKET_NAME") or ""
            if bucket:
                namespace = sec.get("PERSISTENT_CACHE_NAMESPACE", "shared")
                uri = f"gs://{bucket.strip('/')}/{namespace}"
                # Store namespace separately too
                if not os.environ.get("PERSISTENT_CACHE_NAMESPACE"):
                    os.environ["PERSISTENT_CACHE_NAMESPACE"] = str(namespace)
        if uri:
            os.environ["PERSISTENT_CACHE_URI"] = uri

    # 2. Inject GCP service account into env as JSON so _load_gcs_token() picks it up
    if not os.environ.get("GCS_SERVICE_ACCOUNT_JSON"):
        sa = sec.get("gcp_service_account")
        if sa:
            try:
                os.environ["GCS_SERVICE_ACCOUNT_JSON"] = json.dumps(dict(sa))
            except Exception:
                pass

    # 3. Set GCP project from service account if not already set
    if not os.environ.get("GCP_PROJECT"):
        sa = sec.get("gcp_service_account", {})
        project = sa.get("project_id") if sa else None
        if project:
            os.environ["GCP_PROJECT"] = str(project)


# Bootstrap on import — runs once, no-ops gracefully if not in Streamlit context
_bootstrap_from_streamlit_secrets()
def _remote_cache_root() -> str:
    return os.getenv("PERSISTENT_CACHE_URI", "").strip().rstrip("/")


def remote_cache_enabled() -> bool:
    return bool(_remote_cache_root()) and _get_gcs_filesystem() is not None


def _remote_cache_namespace() -> str:
    namespace = os.getenv("PERSISTENT_CACHE_NAMESPACE", "").strip().strip("/")
    return namespace or "shared"


def build_cache_target(
    *,
    filename: str,
    local_dir: Path,
    local_subdir: str | None = None,
) -> str | Path:
    remote_root = _remote_cache_root()
    if remote_root and _get_gcs_filesystem() is not None:
        namespace = _remote_cache_namespace()
        return f"{remote_root}/{namespace}/{filename}"

    target_dir = local_dir / local_subdir if local_subdir else local_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename


def _fallback_local_path(target: str | Path) -> Path:
    if isinstance(target, Path):
        return target
    target_str = str(target)
    if "://" in target_str:
        filename = Path(target_str).name
        try:
            from BackEnd.core.paths import CACHE_DIR
            local_path = CACHE_DIR / filename
        except Exception:
            local_path = Path("BackEnd/cache") / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return local_path
    return Path(target_str)


def target_exists(target: str | Path) -> bool:
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            if fs is not None:
                return fs.exists(str(target))
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote target_exists check failed ({exc}). Falling back to local cache."
            )
            return _fallback_local_path(target).exists()
    return Path(target).exists()


def remove_target(target: str | Path):
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            target_str = str(target)
            if fs and fs.exists(target_str):
                fs.rm(target_str)
                return
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote remove_target failed ({exc}). Falling back to local cache."
            )
    local_p = _fallback_local_path(target)
    if local_p.exists():
        try:
            local_p.unlink()
        except Exception:
            pass


def read_text(target: str | Path, encoding: str = "utf-8") -> str:
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            if fs is not None and fs.exists(str(target)):
                with fs.open(str(target), "r", encoding=encoding) as handle:
                    return handle.read()
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote read_text failed ({exc}). Falling back to local cache."
            )
            local_p = _fallback_local_path(target)
            return local_p.read_text(encoding=encoding) if local_p.exists() else ""
    local_p = Path(target)
    return local_p.read_text(encoding=encoding) if local_p.exists() else ""


def write_text(target: str | Path, content: str, encoding: str = "utf-8"):
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            if fs is not None:
                with fs.open(str(target), "w", encoding=encoding) as handle:
                    handle.write(content)
                return
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote write_text failed ({exc}). Falling back to local cache."
            )
    local_p = _fallback_local_path(target)
    local_p.parent.mkdir(parents=True, exist_ok=True)
    local_p.write_text(content, encoding=encoding)


def read_json(target: str | Path) -> dict[str, Any]:
    raw = read_text(target)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def write_json(target: str | Path, payload: dict[str, Any]):
    write_text(target, json.dumps(payload, indent=2), encoding="utf-8")


def read_parquet(target: str | Path) -> pd.DataFrame:
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            if fs is not None and fs.exists(str(target)):
                with fs.open(str(target), "rb") as handle:
                    return pd.read_parquet(handle)
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote read_parquet failed ({exc}). Falling back to local cache."
            )
            local_p = _fallback_local_path(target)
            if local_p.exists():
                try:
                    return pd.read_parquet(local_p)
                except Exception:
                    return pd.DataFrame()
            return pd.DataFrame()
    local_p = Path(target)
    if local_p.exists():
        try:
            return pd.read_parquet(local_p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def write_parquet(df: pd.DataFrame, target: str | Path, *, index: bool = False):
    if _is_remote_target(target):
        try:
            fs = _remote_fs(target)
            if fs is not None:
                with fs.open(str(target), "wb") as handle:
                    df.to_parquet(handle, index=index)
                return
        except Exception as exc:
            from BackEnd.core.logging_config import get_logger
            get_logger("cache_storage").warning(
                f"Remote write_parquet failed ({exc}). Falling back to local cache."
            )
    local_p = _fallback_local_path(target)
    local_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(local_p, index=index)


def _is_remote_target(target: str | Path) -> bool:
    return isinstance(target, str) and "://" in target


def _remote_fs(target: str | Path):
    target_str = str(target)
    if target_str.startswith("gs://"):
        return _get_gcs_filesystem()
    return None


@lru_cache(maxsize=1)
def _get_gcs_filesystem():
    try:
        import gcsfs
        kwargs: dict[str, Any] = {}
        project = (
            os.getenv("GCP_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCLOUD_PROJECT")
        )
        if project:
            kwargs["project"] = project

        token = _load_gcs_token()
        if token is not None:
            kwargs["token"] = token

        return gcsfs.GCSFileSystem(**kwargs)
    except Exception as exc:
        from BackEnd.core.logging_config import get_logger
        get_logger("cache_storage").warning(
            f"GCS filesystem initialization skipped ({exc}). Falling back to local cache storage."
        )
        return None


def _load_gcs_token() -> Any | None:
    raw_json = (
        os.getenv("GCS_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or ""
    ).strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return raw_json

    encoded = (
        os.getenv("GCS_SERVICE_ACCOUNT_JSON_B64")
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        or ""
    ).strip()
    if encoded:
        try:
            return json.loads(base64.b64decode(encoded).decode("utf-8"))
        except Exception:
            return None

    key_path = (
        os.getenv("GCS_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or ""
    ).strip()
    return key_path or None
