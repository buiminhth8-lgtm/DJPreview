#!/usr/bin/env bash
# T28 演示手工走查脚本（可选）。
# Windows 用户请看 docs/DEMO_T28.md，本脚本面向 bash 环境。
set -u

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "===== ai-music-mvp T28 演示走查 ====="
echo "1. 确认后端已启动且使用 MockProvider："
echo "   export LLM_PROVIDER=mock"
echo "   uvicorn services.api.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "2. 检查后端健康："
if curl -fsS "$BASE_URL/api/v1/health"; then
  echo ""
  echo "   [ok] 后端可访问"
else
  echo ""
  echo "   [warn] 后端不可访问，请先启动后端。"
  exit 1
fi
echo ""
echo "3. 启动前端（另开终端）："
echo "   cd apps/web && npm run dev"
echo "   浏览器打开 http://localhost:5173"
echo ""
echo "4. 在页面按 docs/DEMO_T28.md 的顺序演示："
echo "   - 生成 MusicSpec / MIDI / WAV"
echo "   - 修改副歌 / 查看版本 / 恢复版本"
echo "   - 混音 / Piano Roll / Quality / stems"
echo "   - 导出 / 导入 .aimusic.zip"
echo ""
echo "5. 可选自动化 smoke："
echo "   python scripts/demo_t28_smoke.py --base-url $BASE_URL"
