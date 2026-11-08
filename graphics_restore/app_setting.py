"""恢复画质插件的设置入口。"""

from one_dragon_qt.services.app_setting.app_setting_provider import (
    AppSettingProvider,
    SettingType,
)

from . import const


class GraphicsRestoreAppSetting(AppSettingProvider):
    """恢复画质应用的设置提供者。"""

    app_id = const.APP_ID
    setting_type = SettingType.INTERFACE

    @staticmethod
    def get_setting_cls() -> type:
        from .setting_interface import (
            GraphicsRestoreSettingInterface,
        )

        return GraphicsRestoreSettingInterface
