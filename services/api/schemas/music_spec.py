"""MusicSpec v0.1 —— 音乐方案核心协议。"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TempoSpec(BaseModel):
    """速度信息。"""

    bpm: int = Field(ge=40, le=220, description="每分钟节拍数")
    feel: str | None = Field(default=None, description="速度感觉：slow / medium / fast / rubato 等")


class MeterSpec(BaseModel):
    """拍号。"""

    numerator: int = Field(ge=1, description="拍号分子")
    denominator: int = Field(ge=1, description="拍号分母")


class TonalitySpec(BaseModel):
    """调性。"""

    key: str = Field(min_length=1, description="调性主音，例如 C、D、E、F#、Bb")
    mode: str = Field(min_length=1, description="调式，例如 major、minor、dorian、pentatonic")
    scale: str | None = Field(default=None, description="具体音阶")


class LengthSpec(BaseModel):
    """整曲长度。"""

    bars: int = Field(ge=4, le=256, description="总小节数")


class SectionSpec(BaseModel):
    """曲式段落。"""

    id: str = Field(min_length=1, description="段落标识，例如 intro、verse、chorus、bridge、outro")
    name: str = Field(min_length=1, description="段落名称")
    start_bar: int = Field(ge=1, description="起始小节（从 1 开始）")
    bars: int = Field(ge=1, description="段落小节数")
    energy: float = Field(ge=0, le=1, description="能量 0-1")


class HarmonySectionSpec(BaseModel):
    """某段落对应的和弦进行。"""

    section: str = Field(min_length=1, description="对应段落 id")
    progression: list[str] = Field(min_length=1, description="和弦进行")


class TrackSpec(BaseModel):
    """编曲轨道。"""

    id: str = Field(min_length=1, description="轨道标识")
    role: str = Field(min_length=1, description="轨道角色：melody / harmony / bass / drums / pad / strings 等")
    instrument: str = Field(min_length=1, description="乐器")
    pattern: str | None = Field(default=None, description="演奏型，例如 legato、arpeggio、four_on_floor")
    register: str | None = Field(default=None, description="音区，例如 low、mid、high")
    velocity: int = Field(ge=1, le=127, description="默认力度 1-127")
    enabled_sections: list[str] | None = Field(default=None, description="启用的段落 id，None 表示全部")


class MusicSpec(BaseModel):
    """MusicSpec v0.1 —— 一段音乐作品的完整结构描述。"""

    version: str = Field(default="0.1", description="协议版本")
    title: str = Field(min_length=1, description="作品标题")
    seed: int = Field(description="随机种子，保证可复现")
    language: str = Field(default="zh-CN", description="生成语言")
    prompt: str = Field(description="用户的原始自然语言描述")
    tempo: TempoSpec
    meter: MeterSpec
    tonality: TonalitySpec
    length: LengthSpec
    style: list[str] = Field(default_factory=list, description="风格标签")
    mood: list[str] = Field(default_factory=list, description="情绪标签")
    form: list[SectionSpec] = Field(min_length=1, description="曲式段落，至少一个")
    harmony: list[HarmonySectionSpec] = Field(min_length=1, description="和弦进行，至少一个")
    tracks: list[TrackSpec] = Field(min_length=1, description="编曲轨道，至少一个")
    notes: str | None = Field(default=None, description="补充说明")

    @model_validator(mode="after")
    def _check_sections_within_length(self) -> MusicSpec:
        """校验每个段落的小节范围不超出整曲长度。"""
        total = self.length.bars
        for section in self.form:
            end_bar = section.start_bar + section.bars - 1
            if end_bar > total:
                raise ValueError(
                    f"段落 {section.id!r} 结束于第 {end_bar} 小节，"
                    f"超出整曲小节范围（length.bars={total}）"
                )
        return self
