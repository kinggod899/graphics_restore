"""恢复画质插件的配置。

只存兜底档位：原始档位不在这里，运行时从「降低游戏画质」插件留下的快照里读，
只有那份快照缺失（没装降画质插件、或从没跑过）时才用这里的 fallback_*。

use_fallback_only 打开后，不管快照里记着什么，一律按 fallback_* 恢复。
"""

from one_dragon.base.operation.application.application_config import ApplicationConfig

from . import const


class GraphicsRestoreConfig(ApplicationConfig):

    def __init__(self, instance_idx: int, group_id: str) -> None:
        ApplicationConfig.__init__(
            self,
            app_id=const.APP_ID,
            instance_idx=instance_idx,
            group_id=group_id,
        )

    @property
    def use_fallback_only(self) -> bool:
        """是否只用兜底档位，不读降画质插件的记录。"""
        return self.get('use_fallback_only', False)

    @use_fallback_only.setter
    def use_fallback_only(self, new_value: bool) -> None:
        self.update('use_fallback_only', new_value)

    @property
    def fallback_fps(self) -> str:
        """兜底帧率。开了「只用兜底档位」时它就是唯一目标值。"""
        return self.get('fallback_fps', '60')

    @fallback_fps.setter
    def fallback_fps(self, new_value: str) -> None:
        self.update('fallback_fps', new_value)

    @property
    def fallback_render_scale(self) -> str:
        """没有原始记录时用的渲染精度。"""
        return self.get('fallback_render_scale', '1.0')

    @fallback_render_scale.setter
    def fallback_render_scale(self, new_value: str) -> None:
        self.update('fallback_render_scale', new_value)

    @property
    def fallback_antialias(self) -> str:
        """没有原始记录时用的抗锯齿。"""
        return self.get('fallback_antialias', 'SMAA')

    @fallback_antialias.setter
    def fallback_antialias(self, new_value: str) -> None:
        self.update('fallback_antialias', new_value)

    @property
    def fallback_font(self) -> str:
        """完全没有原始记录时用的字体。"""
        return self.get('fallback_font', '全局细体')

    @fallback_font.setter
    def fallback_font(self, new_value: str) -> None:
        self.update('fallback_font', new_value)
