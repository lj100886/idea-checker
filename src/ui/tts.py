"""语音模块（TTS）：edge-tts生成，Windows mciSendString播放"""
import os
import time
import tempfile
import threading
import ctypes
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CHINESE_VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunyang": "zh-CN-YunyangNeural",
}


class TTS:
    def __init__(self, voice: str = "xiaoxiao", enabled: bool = True):
        self.voice = CHINESE_VOICES.get(voice, CHINESE_VOICES["xiaoxiao"])
        self.enabled = enabled
        self._playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._alias_counter = 0

    def set_voice(self, voice: str):
        if voice in CHINESE_VOICES:
            self.voice = CHINESE_VOICES[voice]

    def speak(self, text: str, block: bool = False):
        if not self.enabled or not text:
            return
        text = text[:500]
        if block:
            self._speak_sync(text)
        else:
            if self._play_thread and self._play_thread.is_alive():
                return
            self._play_thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            self._play_thread.start()

    def _speak_sync(self, text: str):
        try:
            self._playing = True
            tmp_dir = tempfile.gettempdir()
            self._alias_counter += 1
            mp3_path = os.path.join(tmp_dir, f"idea_checker_tts_{self._alias_counter}.mp3")
            import asyncio
            import edge_tts
            async def _generate():
                communicate = edge_tts.Communicate(text, self.voice, rate="+10%")
                await communicate.save(mp3_path)
            asyncio.run(_generate())
            if not os.path.exists(mp3_path):
                return
            self._play_mp3(mp3_path)
            time.sleep(0.5)
            try:
                os.remove(mp3_path)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"TTS失败: {e}")
        finally:
            self._playing = False

    def _play_mp3(self, path: str):
        try:
            alias = f"tts_{self._alias_counter}"
            ctypes.windll.winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f"close {alias}", None, 0, None)
        except Exception as e:
            logger.error(f"播放失败: {e}")

    def stop(self):
        try:
            ctypes.windll.winmm.mciSendStringW("close all", None, 0, None)
        except Exception:
            pass
        self._playing = False

    def is_playing(self) -> bool:
        return self._playing


_tts_instance: Optional[TTS] = None


def get_tts(voice: str = "xiaoxiao", enabled: bool = True) -> TTS:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTS(voice, enabled)
    return _tts_instance
