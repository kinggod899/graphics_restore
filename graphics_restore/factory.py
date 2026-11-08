"""恢复画质插件的应用工厂。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application.application_config import ApplicationConfig
from one_dragon.base.operation.application.application_factory import ApplicationFactory
from one_dragon.base.operation.application_base import Application

from . import const
from .app import GraphicsRestoreApp
from .config import GraphicsRestoreConfig

if TYPE_CHECKING:
    from one_dragon.base.operation.application.application_run_record import (
        AppRunRecord,
    )

    from zzz_od.context.zzz_context import ZContext


class GraphicsRestoreFactory(ApplicationFactory):

    def __init__(self, ctx: ZContext) -> None:
        ApplicationFactory.__init__(self, const)
        self.ctx: ZContext = ctx
        # 排序值不属于 const.py 也不属于 plugin.json，在这里指定。
        # 2900 让本应用排在一条龙最后（通知应用 3000 之前），把画质还原给玩的人用。
        self.priority: int | None = 2900

    def create_application(self, instance_idx: int, group_id: str) -> Application:
        return GraphicsRestoreApp(self.ctx)

    def create_config(self, instance_idx: int, group_id: str) -> ApplicationConfig:
        return GraphicsRestoreConfig(instance_idx=instance_idx, group_id=group_id)

    def create_run_record(self, instance_idx: int) -> AppRunRecord | None:
        """不创建每日运行记录，一条龙每次运行都会执行本应用。"""
        return None
