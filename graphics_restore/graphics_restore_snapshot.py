"""读「降低游戏画质」留下的全局原始档位快照。

快照文件是 plugin_data/graphics_low/graphics_low_snapshot.yml，不带实例目录。
旧版本写在 config/graphics_low_snapshot.yml，新位置找不到时回落到那里。
这里不 import 降画质插件的模块，因为两个插件是各自独立的包、
分开安装，跨插件 import 会在只装恢复画质时直接崩掉。
直接按约定的路径打开同一个文件即可。

文件不存在（没装降画质插件、或从没跑过）时读到的都是空串，
调用方据此回落到兜底档位。
"""

from __future__ import annotations

from pathlib import Path

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.utils import os_utils

LOW_APP_ID: str = 'graphics_low'
FILE_NAME: str = 'graphics_low_snapshot.yml'
LEGACY_DIR: str = 'config'  # 旧版本存放快照的目录，相对一条龙工作目录


class LowSnapshotReader(YamlOperator):
    """只读地打开降画质的快照文件。"""

    def __init__(self, low_data_dir: Path) -> None:
        path = Path(low_data_dir) / FILE_NAME
        if not path.is_file():
            legacy_path = Path(os_utils.get_path_under_work_dir(LEGACY_DIR, FILE_NAME))
            if legacy_path.is_file():
                path = legacy_path
        YamlOperator.__init__(self, str(path))

    @property
    def original_fps(self) -> str:
        """原始帧率，空串表示没有记录。"""
        return self.get('original_fps', '')

    @property
    def original_render_scale(self) -> str:
        """原始渲染精度，空串表示没有记录。"""
        return self.get('original_render_scale', '')

    @property
    def original_antialias(self) -> str:
        """原始抗锯齿，空串表示没有记录。"""
        return self.get('original_antialias', '')

    @property
    def original_font(self) -> str:
        """原始字体选项，空串表示没有记录。

        降画质插件切到「其他」页之后才补记这一项，所以老版本留下的快照里可能没有它，
        那时即使 has_snapshot 为 True，original_font 也还是空串。
        """
        return self.get('original_font', '')

    @property
    def snapshot_date(self) -> str:
        """记录日期，空串表示没有记录。"""
        return self.get('snapshot_date', '')

    @property
    def has_snapshot(self) -> bool:
        """是否有可用的原始档位记录。"""
        return self.original_fps != ''
