"""自然语言修改引擎模块。"""

from packages.music_core.editing.diff import diff_music_specs
from packages.music_core.editing.edit_engine import apply_music_edit

__all__ = ["apply_music_edit", "diff_music_specs"]
