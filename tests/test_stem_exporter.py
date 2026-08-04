"""分轨 stems 导出测试（AUDIO_RENDERER=fallback）。"""

import zipfile

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.mix.mix_engine import create_default_mix_spec
from packages.renderer.stem_renderer import export_stems
from tests.test_harmony_engine import build_spec


def test_export_stems_creates_midi_wav_zip(tmp_path):
    spec = build_spec()
    mix = create_default_mix_spec(spec, song_id="s1", version_id="v1")
    result = export_stems("s1", spec, mix, tmp_path / "stems", sample_rate=8000, gain=0.6)

    assert result.tracks
    midi_files = list((tmp_path / "stems" / "midi").glob("*.mid"))
    wav_files = list((tmp_path / "stems" / "wav").glob("*.wav"))
    assert midi_files
    assert wav_files

    zip_path = tmp_path / "stems" / "stems.zip"
    assert zip_path.exists() and zip_path.stat().st_size > 0
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert any(n.startswith("midi/") and n.endswith(".mid") for n in names)
        assert any(n.startswith("wav/") and n.endswith(".wav") for n in names)

    metadata = (tmp_path / "stems" / "stems_metadata.json").read_text(encoding="utf-8")
    assert "stems.zip" in metadata
    assert result.renderer == "fallback"
