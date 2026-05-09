"""巨量千川数据监控"""
import time
import threading
from datetime import datetime


class JuliangMonitor:
    """监控广告数据并自动调价"""

    def __init__(self, browser_ops, plan_manager):
        self.browser_ops = browser_ops
        self.plan_manager = plan_manager
        self._stop_event = threading.Event()
        self._interval = 900  # 15分钟
        self._target_roi = 1.5  # 默认目标ROI

    def start_monitoring(self, interval: int = 900):
        """开始监控"""
        self._interval = interval
        self._stop_event.clear()
        while not self._stop_event.is_set():
            self._check_plans()
            self._stop_event.wait(self._interval)

    def stop_monitoring(self):
        """停止监控"""
        self._stop_event.set()

    def _check_plans(self):
        """检查所有计划状态"""
        plans = self.plan_manager.load_plans()
        for plan in plans:
            if plan.get("status") == "deleted":
                continue
            metrics = self.get_plan_metrics(plan.get("plan_id"))
            if metrics:
                plan["metrics"] = metrics
                self.plan_manager.save_plan(plan)

    def get_plan_metrics(self, plan_id: str) -> dict:
        """获取计划指标（播放、转化、ROI等）"""
        # 通过浏览器操作获取页面数据
        try:
            if self.browser_ops._page is None:
                return None

            # 导航到计划详情页或刷新列表
            self.browser_ops.navigate_to_live_heating()
            time.sleep(2)

            # 查找对应计划的指标数据
            plan_row = self.browser_ops._page.query_selector(
                f'[data-plan-id="{plan_id}"], [class*="plan-item"]:has-text("{plan_id}")'
            )
            if plan_row:
                impressions = plan_row.query_selector('[class*="impression"], [class*="play"]')
                conversions = plan_row.query_selector('[class*="conversion"], [class*="transform"]')
                roi = plan_row.query_selector('[class*="roi"], [class*="return"]')

                return {
                    "impressions": impressions.inner_text() if impressions and hasattr(impressions, 'inner_text') else "0",
                    "conversions": conversions.inner_text() if conversions and hasattr(conversions, 'inner_text') else "0",
                    "roi": roi.inner_text() if roi and hasattr(roi, 'inner_text') else "0",
                    "updated_at": datetime.now().isoformat(),
                }
            return None
        except Exception:
            return None

    def auto_adjust_bid(self, plan_id: str, target_roi: float = None):
        """根据 ROI 自动调价"""
        if target_roi is not None:
            self._target_roi = target_roi

        metrics = self.get_plan_metrics(plan_id)
        if not metrics:
            return False

        try:
            roi_str = metrics.get("roi", "0")
            # 解析ROI值（可能格式如 "1.5" 或 "150%" 或 "1.5倍"）
            roi_value = 0.0
            if roi_str:
                roi_clean = roi_str.replace("%", "").replace("倍", "").strip()
                try:
                    roi_value = float(roi_clean) / 100 if "%" in roi_str else float(roi_clean)
                except ValueError:
                    roi_value = 0.0

            # 获取当前出价
            current_bid = 0.0
            plan = None
            for p in self.plan_manager.load_plans():
                if p.get("plan_id") == plan_id:
                    plan = p
                    break
            if plan and "bid" in plan:
                current_bid = float(plan.get("bid", 0))

            # 根据ROI自动调价
            adjustment = 0.1  # 每次调整10%
            if roi_value > self._target_roi * 1.2:
                # ROI过高，降低出价
                new_bid = current_bid * (1 - adjustment)
            elif roi_value < self._target_roi * 0.8:
                # ROI过低，升高出价
                new_bid = current_bid * (1 + adjustment)
            else:
                new_bid = current_bid

            # 确保出价在合理范围内
            new_bid = max(0.1, min(new_bid, 1000))

            if abs(new_bid - current_bid) > 0.01:
                return self.browser_ops.adjust_bid(plan_id, new_bid)
            return False
        except Exception:
            return False
