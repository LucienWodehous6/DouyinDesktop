"""巨量千川浏览器自动化操作"""
import time
from typing import Optional


class JuliangBrowserOps:
    """巨量千川浏览器操作类"""

    def __init__(self, cdp_url: str):
        self.cdp_url = cdp_url
        self._page = None
        self._browser = None
        self._playwright = None

    def connect(self):
        """连接到浏览器"""
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        self._page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def disconnect(self):
        """断开连接"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def navigate_to_live_heating(self):
        """导航到直播加热页面"""
        # 进入品牌投放 > 品牌竞价 > 直播加热
        self._page.goto("https://www.oceanengine.com/luopan/brand/live", wait_until="domcontentloaded")
        time.sleep(2)

    def is_logged_in(self) -> bool:
        """检查登录状态"""
        # 检查是否存在登录相关的元素
        if self._page is None:
            return False
        try:
            # 检查是否跳转到登录页
            current_url = self._page.url
            if "login" in current_url.lower():
                return False
            # 检查是否存在用户头像或退出按钮等登录态元素
            login_indicator = self._page.query_selector('[class*="user-info"], [class*="avatar"], [class*="logout"]')
            return login_indicator is not None
        except Exception:
            return False

    def create_plan(self, plan_config: dict) -> dict:
        """创建投放计划"""
        # 填写定向、预算、出价等
        # plan_config 包含: behavior, interest, budget, bid 等
        if self._page is None:
            return {"success": False, "error": "Not connected"}
        try:
            # 导航到直播加热页面
            self.navigate_to_live_heating()
            time.sleep(2)

            # 点击创建计划按钮
            create_btn = self._page.query_selector('button:has-text("创建计划"), button:has-text("新建")')
            if create_btn:
                create_btn.click()
                time.sleep(2)

            # 填写定向设置
            if "behavior" in plan_config:
                behavior_input = self._page.query_selector('input[placeholder*="行为"], input[placeholder*="定向"]')
                if behavior_input:
                    behavior_input.fill(plan_config["behavior"])

            if "interest" in plan_config:
                interest_input = self._page.query_selector('input[placeholder*="兴趣"]')
                if interest_input:
                    interest_input.fill(plan_config["interest"])

            # 填写预算
            if "budget" in plan_config:
                budget_input = self._page.query_selector('input[placeholder*="预算"]')
                if budget_input:
                    budget_input.fill(str(plan_config["budget"]))

            # 填写出价
            if "bid" in plan_config:
                bid_input = self._page.query_selector('input[placeholder*="出价"], input[placeholder*="价格"]')
                if bid_input:
                    bid_input.fill(str(plan_config["bid"]))

            # 提交创建
            submit_btn = self._page.query_selector('button:has-text("提交"), button:has-text("确定"), button:has-text("创建")')
            if submit_btn:
                submit_btn.click()
                time.sleep(3)

            # 获取创建成功的计划ID
            plan_id = None
            url = self._page.url
            if "plan_id" in url or "id=" in url:
                plan_id = url.split("id=")[-1].split("&")[0] if "id=" in url else None

            return {"success": True, "plan_id": plan_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_plan_list(self) -> list:
        """获取计划列表"""
        if self._page is None:
            return []
        try:
            self.navigate_to_live_heating()
            time.sleep(2)

            plans = []
            # 查找计划列表容器
            table_rows = self._page.query_selector_all('table tbody tr, [class*="plan-list"] [class*="item"]')
            for row in table_rows:
                plan_name = row.query_selector('[class*="name"], [class*="title"]')
                status_elem = row.query_selector('[class*="status"]')
                bid_elem = row.query_selector('[class*="bid"], [class*="price"]')
                cost_elem = row.query_selector('[class*="cost"], [class*="consume"]')

                if plan_name:
                    plans.append({
                        "plan_name": plan_name.inner_text() if hasattr(plan_name, 'inner_text') else str(plan_name),
                        "status": status_elem.inner_text() if status_elem and hasattr(status_elem, 'inner_text') else "unknown",
                        "bid": bid_elem.inner_text() if bid_elem and hasattr(bid_elem, 'inner_text') else "0",
                        "cost": cost_elem.inner_text() if cost_elem and hasattr(cost_elem, 'inner_text') else "0",
                    })
            return plans
        except Exception:
            return []

    def pause_plan(self, plan_id: str):
        """暂停计划"""
        if self._page is None:
            return False
        try:
            # 找到对应的计划行并点击暂停按钮
            plan_row = self._page.query_selector(f'[data-plan-id="{plan_id}"], [class*="plan-item"]:has-text("{plan_id}")')
            if plan_row:
                pause_btn = plan_row.query_selector('button:has-text("暂停"), [class*="pause"]')
                if pause_btn:
                    pause_btn.click()
                    time.sleep(1)
                    return True
            return False
        except Exception:
            return False

    def resume_plan(self, plan_id: str):
        """恢复计划"""
        if self._page is None:
            return False
        try:
            plan_row = self._page.query_selector(f'[data-plan-id="{plan_id}"], [class*="plan-item"]:has-text("{plan_id}")')
            if plan_row:
                resume_btn = plan_row.query_selector('button:has-text("启动"), button:has-text("恢复"), [class*="resume"], [class*="start"]')
                if resume_btn:
                    resume_btn.click()
                    time.sleep(1)
                    return True
            return False
        except Exception:
            return False

    def adjust_bid(self, plan_id: str, new_bid: float):
        """调整出价"""
        if self._page is None:
            return False
        try:
            plan_row = self._page.query_selector(f'[data-plan-id="{plan_id}"], [class*="plan-item"]:has-text("{plan_id}")')
            if plan_row:
                bid_input = plan_row.query_selector('input[class*="bid"], input[class*="price"]')
                if bid_input:
                    bid_input.fill(str(new_bid))
                    time.sleep(1)
                    # 确认修改
                    confirm_btn = self._page.query_selector('button:has-text("确认"), button:has-text("确定")')
                    if confirm_btn:
                        confirm_btn.click()
                    return True
            return False
        except Exception:
            return False

    def delete_plan(self, plan_id: str):
        """删除计划"""
        if self._page is None:
            return False
        try:
            plan_row = self._page.query_selector(f'[data-plan-id="{plan_id}"], [class*="plan-item"]:has-text("{plan_id}")')
            if plan_row:
                delete_btn = plan_row.query_selector('button:has-text("删除"), [class*="delete"]')
                if delete_btn:
                    delete_btn.click()
                    time.sleep(1)
                    # 确认删除
                    confirm_btn = self._page.query_selector('button:has-text("确认"), button:has-text("确定"), [class*="confirm-delete"]')
                    if confirm_btn:
                        confirm_btn.click()
                    return True
            return False
        except Exception:
            return False
