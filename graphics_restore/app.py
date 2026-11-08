"""恢复游戏画质应用。

执行链路：传送录像店 → 回到大世界 → 点左上「菜单」开暂停菜单 → 点底部「设置」
→ 确认停在「画面」页签 → 读「降低游戏画质」插件留下的快照 → 逐项改回去
→ 切到「其他」页签 → 改字体选项 → 连点两次返回回到大世界。

快照读不到时（没装降画质插件 / 从没跑过）用配置里的兜底档位。
设置里打开「只用兜底档位」后，不再读快照，一律按兜底档位恢复。
快照是旧版本记的、里面没有 original_font 时不动字体。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.application import application_const
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.log_utils import log
from zzz_od.application.zzz_application import ZApplication
from zzz_od.operation.back_to_normal_world import BackToNormalWorld
from zzz_od.operation.transport import Transport

from . import const
from . import screen as graphics_restore_screen  # 别名避开函数内表示截图的 screen 变量
from .config import GraphicsRestoreConfig
from .graphics_restore_snapshot import LOW_APP_ID, LowSnapshotReader
from .screen import GraphicsRow

if TYPE_CHECKING:
    from numpy import ndarray

    from one_dragon.base.geometry.point import Point
    from one_dragon.base.geometry.rectangle import Rect
    from zzz_od.context.zzz_context import ZContext


class GraphicsRestoreApp(ZApplication):
    """把帧率、渲染精度、抗锯齿、字体恢复成降画质前的档位。"""

    def __init__(self, ctx: ZContext) -> None:
        ZApplication.__init__(
            self,
            ctx=ctx,
            app_id=const.APP_ID,
            op_name=const.APP_NAME,
        )
        self.config: GraphicsRestoreConfig = self.ctx.run_context.get_config(
            app_id=const.APP_ID,
            instance_idx=self.ctx.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )
        # 目标档位在节点里才解析，构造时不碰其它插件的配置
        self.targets: dict[str, str] = {}

    # ─── 通用小工具 ────────────────────────────────────────

    def _click_point(self, point: Point, wait: float) -> None:
        """点一个固定坐标并等界面响应。"""
        self.ctx.controller.click(point, press_time=0.1, pc_alt=True)
        time.sleep(wait)

    def _click_keyword(self, screen: ndarray, rect: Rect, keyword: str) -> bool:
        """在指定区域内 OCR 找到关键字就点它，找不到返回 False。"""
        matches = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=rect, crop_first=True,
        )
        for match in matches:
            # 阈值偏高是故意的：这里点错一下会跳到别的页签，代价比多试一轮大得多
            if str_utils.find_by_lcs(keyword, match.data, percent=0.8):
                self.ctx.controller.click(match.center, press_time=0.1, pc_alt=True)
                return True
        return False

    def _read_row_value(self, screen: ndarray, row: GraphicsRow) -> str:
        """读一行下拉框的当前值，读不到或认不出返回空串。

        值区右侧还有下拉箭头，OCR 会把箭头一起读进来，所以这里不是直接返回
        OCR 原文，而是拿原文去和该行的候选项对一遍，命中哪个就返回哪个。
        """
        matches = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=row.value_rect(), crop_first=True,
        )
        text = ''.join(match.data for match in sorted(matches, key=lambda item: (item.y, item.x)))
        text = text.replace(' ', '').strip()
        if text == '':
            return ''
        for option in row.options:
            if option in text:
                return option
        for option in row.options:
            # 这里必须要求逐字全中：1.0 和 1.2 的公共子序列长度是 2，
            # 松阈值会让 1.2 被认成 1.0，后面就会误判成"已经是目标值"
            if str_utils.find_by_lcs(option, text, percent=1.0):
                return option
        return ''

    def _has_font_row(self, screen: ndarray) -> bool:
        """右侧标签列里有没有「字体选项」，用它判断当前在不在「其他」页。"""
        matches = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=graphics_restore_screen.LABEL_COLUMN, crop_first=True,
        )
        for match in matches:
            if str_utils.find_by_lcs(
                graphics_restore_screen.OTHER_PANEL_KEYWORD, match.data, percent=0.8,
            ):
                return True
        return False

    def _apply_row(self, row: GraphicsRow, target: str) -> OperationRoundResult:
        """把一行下拉框改成目标值。

        下拉框展开后，选项文字会和行内当前值重复，所以只能按固定几何点选，
        不能在全屏里搜索目标文字。
        """
        if target == '':
            return self.round_success(status=f'{row.label} 没有目标值，跳过')
        if row.option_index(target) < 0:
            return self.round_fail(status=f'{row.label} 目标值 {target} 不在可选项里')

        screen = self.screenshot()
        current = self._read_row_value(screen, row)
        if current == target:
            return self.round_success(status=f'{row.label} 已经是 {target}')

        self._click_point(row.value_point(), graphics_restore_screen.DROPDOWN_OPEN_WAIT)
        option_point = row.dropdown_point(target)
        if option_point is None:
            return self.round_fail(status=f'{row.label} 找不到选项 {target}')
        self._click_point(option_point, graphics_restore_screen.DROPDOWN_PICK_WAIT)
        self._click_point(graphics_restore_screen.BLANK_POINT, graphics_restore_screen.DROPDOWN_CLOSE_WAIT)

        screen = self.screenshot()
        after = self._read_row_value(screen, row)
        if after == target:
            return self.round_success(status=f'{row.label} {current} -> {target}')
        if after == '':
            # 读不到值不代表没改成功，按已改处理，避免因为 OCR 不稳把整条链路判失败
            log.warning(f'{row.label} 改完后读不到当前值，按已改成 {target} 处理')
            return self.round_success(status=f'{row.label} -> {target}')
        return self.round_retry(status=f'{row.label} 改动未生效，当前 {after}')

    def _resolve_targets(self) -> None:
        """决定三个目标值：默认读降画质插件留下的快照，缺项用兜底档位补。"""
        if self.config.use_fallback_only:
            log.info('已开启「只用兜底档位」，不读降画质插件的记录')
            self.targets = {
                'fps': self.config.fallback_fps,
                'render_scale': self.config.fallback_render_scale,
                'antialias': self.config.fallback_antialias,
                'font': self.config.fallback_font,
            }
            return

        try:
            snapshot = LowSnapshotReader(self.ctx.get_plugin_data_dir(LOW_APP_ID))
        except Exception:
            log.warning('读不到「降低游戏画质」的快照，改用兜底档位', exc_info=True)
            snapshot = None

        self.targets = {
            'fps': (snapshot.original_fps if snapshot else '') or self.config.fallback_fps,
            'render_scale': (
                (snapshot.original_render_scale if snapshot else '')
                or self.config.fallback_render_scale
            ),
            'antialias': (
                (snapshot.original_antialias if snapshot else '')
                or self.config.fallback_antialias
            ),
            'font': self._resolve_font(snapshot),
        }

    def _resolve_font(self, snapshot: LowSnapshotReader | None) -> str:
        """字体这一项目标值的取法，和上面三项略有不同。

        完全没有记录（快照里的 original_fps 都是空的）时，和上面三项一样落到兜底字体。
        但快照有记录、只是没有 original_font 时不能落到兜底：那是老版本记下的快照，
        当时降画质插件还没开始改字体，说明字体没被动过，兜底值反而会覆盖用户自己的选择。
        这种情况返回空串，调用方会整段跳过字体。
        """
        if snapshot is None:
            return self.config.fallback_font
        if snapshot.original_font != '':
            return snapshot.original_font
        if snapshot.has_snapshot:
            log.warning('快照里没有原始字体（旧版本记录），本次不恢复字体')
            return ''
        return self.config.fallback_font

    # ─── 节点 ─────────────────────────────────────────────

    @operation_node(name='传送录像店', is_start_node=True, screenshot_before_round=False)
    def teleport_to_video_store(self) -> OperationRoundResult:
        op = Transport(self.ctx, '录像店', '房间')
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送录像店')
    @operation_node(name='回到大世界', screenshot_before_round=False)
    def back_to_world(self) -> OperationRoundResult:
        op = BackToNormalWorld(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='回到大世界')
    @operation_node(name='打开暂停菜单', screenshot_before_round=False, node_max_retry_times=5)
    def open_pause_menu(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            screen=self.screenshot(),
            screen_name=graphics_restore_screen.WORLD_SCREEN_NAME,
            area_name=graphics_restore_screen.WORLD_MENU_BUTTON_AREA,
            success_wait=graphics_restore_screen.MENU_WAIT,
            retry_wait=1,
        )

    @node_from(from_name='打开暂停菜单')
    @operation_node(name='点击设置', screenshot_before_round=False, node_max_retry_times=5)
    def click_settings(self) -> OperationRoundResult:
        screen = self.screenshot()
        if self._click_keyword(screen, graphics_restore_screen.PAUSE_BOTTOM_BAR,
                               graphics_restore_screen.PAUSE_MENU_KEYWORD):
            time.sleep(graphics_restore_screen.MENU_WAIT)
            return self.round_success('已点设置')
        return self.round_retry('暂停菜单里没找到设置', wait=1)

    @node_from(from_name='点击设置')
    @operation_node(name='确认画面页', screenshot_before_round=False, node_max_retry_times=5)
    def ensure_render_tab(self) -> OperationRoundResult:
        screen = self.screenshot()
        matches = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=graphics_restore_screen.LABEL_COLUMN, crop_first=True,
        )
        for match in matches:
            if str_utils.find_by_lcs(
                graphics_restore_screen.RENDER_PANEL_KEYWORD, match.data, percent=0.8,
            ):
                return self.round_success('已在画面页')
        if self._click_keyword(screen, graphics_restore_screen.TAB_COLUMN,
                               graphics_restore_screen.RENDER_TAB_KEYWORD):
            time.sleep(graphics_restore_screen.MENU_WAIT)
            return self.round_success('已切到画面页')
        return self.round_retry('设置界面里没找到画面页签', wait=1)

    @node_from(from_name='确认画面页')
    @operation_node(name='确定目标档位', screenshot_before_round=False)
    def resolve_targets(self) -> OperationRoundResult:
        self._resolve_targets()
        return self.round_success(f'目标档位 {self.targets}')

    @node_from(from_name='确定目标档位')
    @operation_node(name='恢复帧率', screenshot_before_round=False)
    def restore_fps(self) -> OperationRoundResult:
        return self._apply_row(graphics_restore_screen.FPS_ROW, self.targets.get('fps', ''))

    @node_from(from_name='恢复帧率')
    @operation_node(name='恢复渲染精度', screenshot_before_round=False)
    def restore_render_scale(self) -> OperationRoundResult:
        return self._apply_row(graphics_restore_screen.RENDER_SCALE_ROW, self.targets.get('render_scale', ''))

    @node_from(from_name='恢复渲染精度')
    @operation_node(name='恢复抗锯齿', screenshot_before_round=False)
    def restore_antialias(self) -> OperationRoundResult:
        return self._apply_row(graphics_restore_screen.ANTIALIAS_ROW, self.targets.get('antialias', ''))

    @node_from(from_name='恢复抗锯齿')
    @operation_node(name='切到其他页签', screenshot_before_round=False, node_max_retry_times=5)
    def switch_to_other_tab(self) -> OperationRoundResult:
        """字体在「其他」页。没有目标字体时整段跳过，不白切一次页签。"""
        if self.targets.get('font', '') == '':
            return self.round_success('没有目标字体，跳过')
        if self._has_font_row(self.screenshot()):
            return self.round_success('已在其他页')
        self._click_point(graphics_restore_screen.OTHER_TAB_POINT, graphics_restore_screen.MENU_WAIT)
        if self._has_font_row(self.screenshot()):
            return self.round_success('已切到其他页')
        return self.round_retry('没切到其他页', wait=1)

    @node_from(from_name='切到其他页签')
    @operation_node(name='恢复字体', screenshot_before_round=False)
    def restore_font(self) -> OperationRoundResult:
        return self._apply_row(
            graphics_restore_screen.FONT_ROW, self.targets.get('font', ''),
        )

    @node_from(from_name='恢复字体')
    @operation_node(name='返回大世界', screenshot_before_round=False)
    def back_out(self) -> OperationRoundResult:
        self._click_point(graphics_restore_screen.BACK_POINT, graphics_restore_screen.BACK_WAIT)
        self._click_point(graphics_restore_screen.BACK_POINT, graphics_restore_screen.BACK_WAIT)
        op = BackToNormalWorld(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug() -> None:
    from one_dragon.base.operation.application import application_const
    from zzz_od.context.zzz_context import ZContext

    ctx = ZContext()
    ctx.init()
    ctx.run_context.run_application(
        app_id=const.APP_ID,
        instance_idx=ctx.current_instance_idx,
        group_id=application_const.DEFAULT_GROUP_ID,
    )


if __name__ == '__main__':
    __debug()
