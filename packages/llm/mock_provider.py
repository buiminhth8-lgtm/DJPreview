"""MockProvider —— 不调用任何外部 API，按规则生成合法 MusicSpec。"""

from __future__ import annotations

import zlib

from packages.llm.base import LLMProvider
from services.api.schemas.music_edit_spec import EditOperation, EditTarget, MusicEditSpec
from services.api.schemas.music_spec import (
    HarmonySectionSpec,
    LengthSpec,
    MeterSpec,
    MusicSpec,
    SectionSpec,
    TempoSpec,
    TonalitySpec,
    TrackSpec,
)


class MockProvider(LLMProvider):
    """基于规则关键词的模拟 Provider，保证输出始终合法。"""

    name = "mock"

    _MINOR_KEYWORDS = ("忧郁", "悲伤", "雨夜", "伤感")
    _MAJOR_KEYWORDS = ("欢快", "明亮")
    _PENTATONIC_KEYWORD = "中国风"

    def generate_music_spec(self, prompt: str) -> MusicSpec:
        prompt_clean = prompt.strip()
        lower = prompt_clean.lower()

        # 调式 / 调性 / 速度
        is_pentatonic = self._PENTATONIC_KEYWORD in prompt_clean
        if any(k in prompt_clean for k in self._MINOR_KEYWORDS):
            key, mode, scale, bpm = "D", "minor", "d-natural-minor", 72
        elif any(k in prompt_clean for k in self._MAJOR_KEYWORDS):
            key, mode, scale, bpm = "C", "major", "c-major", 120
        else:
            key, mode, scale, bpm = "C", "major", "c-major", 120
        if is_pentatonic:
            mode = "pentatonic"
            scale = "c-major-pentatonic"

        chords = ["Dm", "Bb", "F", "C"] if mode == "minor" else ["C", "G", "Am", "F"]

        # 默认曲式：intro 4 + verse 8 + chorus 16 + outro 4 = 32 小节
        sections = [
            SectionSpec(id="intro", name="前奏", start_bar=1, bars=4, energy=0.2),
            SectionSpec(id="verse", name="主歌", start_bar=5, bars=8, energy=0.5),
            SectionSpec(id="chorus", name="副歌", start_bar=13, bars=16, energy=0.9),
            SectionSpec(id="outro", name="尾奏", start_bar=29, bars=4, energy=0.3),
        ]

        harmony = [
            HarmonySectionSpec(section="intro", progression=[chords[0]]),
            HarmonySectionSpec(section="verse", progression=chords),
            HarmonySectionSpec(section="chorus", progression=[*chords, chords[1], chords[0]]),
            HarmonySectionSpec(section="outro", progression=[chords[0]]),
        ]

        tracks = [
            TrackSpec(id="melody", role="melody", instrument="lead_synth", pattern="legato", register="mid-high", velocity=100),
            TrackSpec(id="piano", role="harmony", instrument="piano", pattern="comping", register="mid", velocity=80),
            TrackSpec(id="bass", role="bass", instrument="bass", pattern="roots", register="low", velocity=90),
            TrackSpec(id="drums", role="drums", instrument="drums", pattern="four_on_floor", register=None, velocity=100),
            TrackSpec(id="pad", role="pad", instrument="strings", pattern="sustained", register="mid-low", velocity=70),
        ]

        # 标题取 prompt 前 16 个字符；seed 用 crc32 保证跨进程确定性
        title = prompt_clean[:16] or "Untitled"
        seed = zlib.crc32(prompt_clean.encode("utf-8"))

        return MusicSpec(
            version="0.1",
            title=title,
            seed=seed,
            language="zh-CN",
            prompt=prompt_clean,
            tempo=TempoSpec(bpm=bpm, feel="slow" if bpm <= 80 else "medium"),
            meter=MeterSpec(numerator=4, denominator=4),
            tonality=TonalitySpec(key=key, mode=mode, scale=scale),
            length=LengthSpec(bars=32),
            style=["pop"],
            mood=["calm"] if mode == "minor" else ["bright"],
            form=sections,
            harmony=harmony,
            tracks=tracks,
            notes=f"由 MockProvider 根据提示词生成：{prompt_clean}",
        )

    def generate_music_edit(self, instruction: str, current_spec: MusicSpec) -> MusicEditSpec:
        """规则化生成修改协议：识别速度、调性、轨道等关键词。"""
        text = instruction.strip()
        target = EditTarget(scope="partial")

        if any(k in text for k in ("整首", "整体", "全局")):
            target = EditTarget(scope="overall")
        elif "bass" in text or "贝斯" in text:
            target = EditTarget(scope="track", track="bass")
        elif "drums" in text or "鼓" in text:
            target = EditTarget(scope="track", track="drums")
        elif "melody" in text or "旋律" in text:
            target = EditTarget(scope="track", track="melody")
        elif "chorus" in text or "副歌" in text:
            target = EditTarget(scope="section", section="chorus")
        elif "verse" in text or "主歌" in text:
            target = EditTarget(scope="section", section="verse")

        operations: list[EditOperation] = []
        if any(k in text for k in ("更快", "加速")):
            operations.append(EditOperation(type="tempo", amount=10.0, params={"bpm": current_spec.tempo.bpm + 10}))
        if any(k in text for k in ("更慢", "减速")):
            operations.append(EditOperation(type="tempo", amount=-10.0, params={"bpm": max(40, current_spec.tempo.bpm - 10)}))
        if "更亮" in text or "明亮" in text:
            operations.append(EditOperation(type="tonality", value="C"))
        if "更暗" in text or "忧郁" in text:
            operations.append(EditOperation(type="tonality", value="D", params={"mode": "minor"}))
        if "音量" in text or "力度" in text:
            operations.append(EditOperation(type="velocity", amount=5.0))

        return MusicEditSpec(
            version="0.1",
            instruction=text,
            target=target,
            preserve=["version", "seed", "prompt"],
            operations=operations,
        )
