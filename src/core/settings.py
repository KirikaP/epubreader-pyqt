"""设置管理模块"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class SettingsManager:
    """用户设置管理器"""

    DEFAULT_FILE = ".epub_reader_pyqt.json"

    def __init__(self, filename: Optional[str] = None):
        self._settings_file = str(Path.home() / (filename or self.DEFAULT_FILE))

    def save(self, data: Dict[str, Any]) -> bool:
        """保存设置到文件"""
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load(self) -> Dict[str, Any]:
        """从文件加载设置"""
        try:
            if os.path.exists(self._settings_file):
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """获取单个设置项"""
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置单个设置项"""
        data = self.load()
        data[key] = value
        return self.save(data)
