"""MockProvider —— 不调用任何外部 API，按规则生成合法 MusicSpec / MusicEditSpec。"""

from __future__ import annotations

import zlib

from packages.llm.base import LLMProvider, T
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

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        task_name: str,
        project_id: str | None = None,
        retries: int = 2,
    ) -> T:
        """Mock 版结构化调用：不发起网络请求、不依赖 API Key。

        MusicSpec 直接复用规则生成器；其余模型请使用
        generate_music_spec / generate_music_edit 专用方法。
        """
        if response_model is MusicSpec:
            return self.generate_music_spec(user_prompt)  # type: ignore[return-value]
        raise ValueError(
            f"MockProvider.generate_structured 不支持 {response_model.__name__}，"
            "请使用 generate_music_spec / generate_music_edit"
        )

    def generate_music_spec(self, prompt: str) -> MusicSpec:
        prompt_clean = prompt.strip()

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

        style_tags: list[str] = []
        if "中国风" in prompt_clean or "chinese" in prompt_clean.lower():
            style_tags.append("chinese")
        if any(k in prompt_clean.lower() for k in ("lo-fi", "lofi", "hiphop")):
            style_tags.append("lo-fi")
        if any(k in prompt_clean.lower() for k in ("摇滚", "rock")):
            style_tags.append("rock")
        if not style_tags:
            style_tags = ["pop"]

        if "lo-fi" in style_tags:
            chords = ["Cmaj7", "Am7", "Dm7", "G7"]
        elif mode == "minor":
            chords = ["Dm", "Bb", "F", "C"]
        else:
            chords = ["C", "G", "Am", "F"]

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
            TrackSpec(id="melody", role="melody", instrument="lead_1_square", pattern="legato", register="mid-high", velocity=100),
            TrackSpec(id="piano", role="harmony", instrument="acoustic_grand_piano", pattern="comping", register="mid", velocity=80),
            TrackSpec(id="bass", role="bass", instrument="electric_bass_finger", pattern="roots", register="low", velocity=90),
            TrackSpec(id="drums", role="drums", instrument="standard_drum_kit", pattern="four_on_floor", register=None, velocity=100),
            TrackSpec(id="pad", role="pad", instrument="string_ensemble_1", pattern="sustained", register="mid-low", velocity=70),
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
            style=style_tags,
            mood=["calm"] if mode == "minor" else ["bright"],
            form=sections,
            harmony=harmony,
            tracks=tracks,
            notes=f"由 MockProvider 根据提示词生成：{prompt_clean}",
        )

    def generate_music_edit(
        self,
        instruction: str,
        current_spec: MusicSpec,
        project_id: str | None = None,
    ) -> MusicEditSpec:
        """规则化生成修改协议：识别段落/轨道目标与常见中文指令。

        project_id 仅用于与 DeepSeekProvider 保持统一签名（Mock 不写日志）。
        """
        text = instruction.strip()
        target = self._parse_edit_target(text)

        # 加/去乐器时避免被误判为轨道目标
        if any(k in text for k in (
            "加钢琴", "加鼓", "加弦乐", "加 pad", "加铺底",
            "去掉鼓", "删除鼓", "不要鼓", "去掉贝斯", "删除贝斯", "不要贝斯",
            "去掉钢琴", "删除钢琴",
        )):
            if target.scope == "track":
                target = EditTarget(scope="partial")

        operations: list[EditOperation] = []

        if "中国风" in text:
            operations.append(EditOperation(type="chinese_style", value="pentatonic"))

        if any(k in text for k in ("更快", "加速")):
            operations.append(EditOperation(type="tempo", amount=10.0, params={"bpm": current_spec.tempo.bpm + 10}))
        if any(k in text for k in ("更慢", "减速")):
            operations.append(EditOperation(type="tempo", amount=-10.0, params={"bpm": max(40, current_spec.tempo.bpm - 10)}))

        if target.section is not None:
            # 段落目标：亮度/暗度映射为段落能量变化
            if "更亮" in text or "明亮" in text or "更激昂" in text or "更强" in text:
                operations.append(EditOperation(type="energy", amount=0.15))
            if "更暗" in text or "更柔" in text or "平静" in text or "舒缓" in text:
                operations.append(EditOperation(type="energy", amount=-0.15))
        else:
            if "更亮" in text or "明亮" in text:
                operations.append(EditOperation(type="tonality", value="C", params={"mode": "major"}))
            if "更暗" in text or "忧郁" in text or "悲伤" in text:
                operations.append(EditOperation(type="tonality", value="D", params={"mode": "minor"}))

        if any(k in text for k in ("更激昂", "更强", "更有力")):
            operations.append(EditOperation(type="energy", amount=0.15))
        if any(k in text for k in ("更柔和", "更平静", "更舒缓")):
            operations.append(EditOperation(type="energy", amount=-0.15))

        if "音量" in text or "力度" in text:
            operations.append(EditOperation(type="velocity", amount=5.0))

        if any(k in text for k in ("加钢琴", "加个钢琴")):
            operations.append(EditOperation(type="add_instrument", value="piano", params={"role": "harmony"}))
        if any(k in text for k in ("加鼓", "加个鼓", "加打击乐")):
            operations.append(EditOperation(type="add_instrument", value="drums", params={"role": "drums"}))
        if any(k in text for k in ("加弦乐", "加 pad", "加铺底")):
            operations.append(EditOperation(type="add_instrument", value="strings", params={"role": "pad"}))

        if any(k in text for k in ("去掉鼓", "删除鼓", "不要鼓")):
            operations.append(EditOperation(type="remove_instrument", value="drums"))
        if any(k in text for k in ("去掉贝斯", "删除贝斯", "不要贝斯")):
            operations.append(EditOperation(type="remove_instrument", value="bass"))
        if any(k in text for k in ("去掉钢琴", "删除钢琴")):
            operations.append(EditOperation(type="remove_instrument", value="piano"))

        return MusicEditSpec(
            version="0.1",
            instruction=text,
            target=target,
            preserve=["version", "seed", "prompt", "language"],
            operations=operations,
        )

    @staticmethod
    def _parse_edit_target(text: str) -> EditTarget:
        """按指令关键词解析修改目标（段落优先于轨道）。"""
        if any(k in text for k in ("整首", "整体", "全局")):
            return EditTarget(scope="overall")
        if "chorus" in text or "副歌" in text:
            return EditTarget(scope="section", section="chorus")
        if "verse" in text or "主歌" in text:
            return EditTarget(scope="section", section="verse")
        if "intro" in text or "前奏" in text:
            return EditTarget(scope="section", section="intro")
        if "outro" in text or "尾奏" in text:
            return EditTarget(scope="section", section="outro")
        if "bass" in text or "贝斯" in text:
            return EditTarget(scope="track", track="bass")
        if "drums" in text or "鼓" in text:
            return EditTarget(scope="track", track="drums")
        if "melody" in text or "旋律" in text:
            return EditTarget(scope="track", track="melody")
        return EditTarget(scope="partial")
