"""版本资产目录式结构（T12 第一步）与完整资产恢复（T13）。"""

from packages.music_core.versioning.version_assets import (
    MANAGED_VERSION_ASSETS,
    copy_current_assets_to_version,
    mirror_stems_to_root,
    restore_version_assets_to_current,
)
from packages.music_core.versioning.version_migration import ensure_version_layout
from packages.music_core.versioning.version_models import (
    VersionIndex,
    VersionIndexEntry,
    VersionMeta,
)

__all__ = [
    "VersionIndex",
    "VersionIndexEntry",
    "VersionMeta",
    "MANAGED_VERSION_ASSETS",
    "copy_current_assets_to_version",
    "ensure_version_layout",
    "mirror_stems_to_root",
    "restore_version_assets_to_current",
]
