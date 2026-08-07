import { useEffect, useRef, useState } from "react";

interface AudioPlayerProps {
  audioUrl: string;
  downloadUrl: string;
}

export default function AudioPlayer({ audioUrl, downloadUrl }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPlaying(false);
    setLoading(true);
    setError(null);
  }, [audioUrl]);

  const togglePlay = () => {
    const el = audioRef.current;
    if (!el) return;
    if (el.paused) {
      el.play().catch(() => setError("播放失败，请检查浏览器是否支持 WAV 播放"));
    } else {
      el.pause();
    }
  };

  return (
    <div className="audio-player">
      <audio
        ref={audioRef}
        src={audioUrl}
        controls
        preload="metadata"
        onCanPlay={() => setLoading(false)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onError={() => {
          setLoading(false);
          setError("音频加载失败");
        }}
      />
      <div className="audio-actions">
        <button onClick={togglePlay} disabled={loading}>
          {loading ? "加载中…" : playing ? "暂停" : "播放"}
        </button>
        <a className="download-link" href={downloadUrl} download>
          下载 WAV
        </a>
      </div>
      {error && <div className="error">⚠ {error}</div>}
    </div>
  );
}
