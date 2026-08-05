"""FluidSynth 渲染器：通过系统命令调用 fluidsynth（不依赖 pyfluidsynth）。"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from packages.renderer.audio_metadata import AudioRenderResult, get_wav_duration_seconds

logger = logging.getLogger(__name__)

# 常见 SoundFont 路径（SOUNDFONT_PATH 为空时自动尝试）
_COMMON_SOUNDFONTS = (
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/FluidR3_GS.sf2",
    "/usr/share/sounds/sf2/FluidR3_GM.sf3",
    "/usr/share/sounds/sf2/default.sf2",
    "/usr/share/soundfonts/default.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
)


class FluidSynthRenderer:
    """使用系统 fluidsynth 命令渲染 MIDI → WAV。"""

    name = "fluidsynth"

    def __init__(self, binary: str | None = None, soundfont: str | None = None) -> None:
        self.binary = binary or os.getenv("FLUIDSYNTH_BIN", "") or "fluidsynth"
        self.soundfont = soundfont if soundfont is not None else os.getenv("SOUNDFONT_PATH", "")

    def is_available(self) -> tuple[bool, list[str]]:
        """检查 fluidsynth 与 SoundFont 是否可用，返回 (可用, 警告列表)。"""
        warnings: list[str] = []
        if shutil.which(self.binary) is None:
            warnings.append("未找到 fluidsynth 可执行文件，请安装 FluidSynth 或设置 AUDIO_RENDERER=fallback")
            return False, warnings
        if self._find_soundfont() is None:
            warnings.append("未找到 SoundFont，请设置 SOUNDFONT_PATH 或安装 fluid-soundfont-gm")
            return False, warnings
        return True, warnings

    def _find_soundfont(self, override: str | Path | None = None) -> Path | None:
        if override:
            candidate = Path(override)
            return candidate if candidate.exists() else None
        if self.soundfont:
            candidate = Path(self.soundfont)
            if candidate.exists():
                return candidate
        for candidate in _COMMON_SOUNDFONTS:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def render_wav(
        self,
        midi_path: Path,
        wav_path: Path,
        *,
        sample_rate: int = 44100,
        gain: float = 0.6,
        soundfont_path: Path | str | None = None,
    ) -> AudioRenderResult:
        exe = shutil.which(self.binary)
        if exe is None:
            raise RuntimeError(
                "未找到 fluidsynth 可执行文件，请安装 FluidSynth，"
                "或将 AUDIO_RENDERER 设为 fallback 使用开发兜底渲染。"
            )
        soundfont = self._find_soundfont(soundfont_path)
        if soundfont is None:
            raise RuntimeError(
                "未找到 SoundFont 文件，请设置 SOUNDFONT_PATH 环境变量，"
                "或将 AUDIO_RENDERER 设为 fallback 使用开发兜底渲染。"
            )

        wav_path = Path(wav_path)
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        # 使用参数列表调用，不使用 shell=True，保证安全
        command = [
            exe,
            "-ni",
            str(soundfont),
            str(midi_path),
            "-F",
            str(wav_path),
            "-r",
            str(sample_rate),
            "-g",
            str(gain),
        ]
        logger.info("FluidSynth 渲染命令：%s", " ".join(command))
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("FluidSynth 渲染超时（600s）") from exc
        except OSError as exc:
            raise RuntimeError(f"FluidSynth 启动失败：{exc}") from exc

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-500:]
            raise RuntimeError(f"FluidSynth 渲染失败（exit={proc.returncode}）：{detail}")
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise RuntimeError("FluidSynth 未生成有效的 output.wav")

        warnings: list[str] = []
        if proc.stderr and proc.stderr.strip():
            warnings.append(proc.stderr.strip()[-300:])
        return AudioRenderResult(
            wav_path=wav_path,
            renderer=self.name,
            sample_rate=sample_rate,
            duration_seconds=get_wav_duration_seconds(wav_path),
            file_size=wav_path.stat().st_size,
            warnings=warnings,
        )
