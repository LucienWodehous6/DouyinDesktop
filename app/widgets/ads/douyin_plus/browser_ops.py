"""抖音 DO+ 浏览器自动化操作"""
import time
import re
from typing import Optional


class DouyinPlusBrowserOps:
    """抖音 DO+ 浏览器操作类 — 通过 Playwright CDP 操作 DO+ 推广后台"""

    # 抖音 DO+ URL
    DO_PLUS_HOME_URL = "https://www.douyin.com/plus"
    DO_PLUS_PROMOTE_URL = "https://www.douyin.com/plus/promo/list"

    def __init__(self, cdp_url: str):
        self.cdp_url = cdp_url
        self._page = None
        self._browser = None
        self._playwright = None

    def connect(self) -> bool:
        """连接到浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)
            ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
            self._page = ctx.pages[0] if ctx.pages else ctx.new_page()
            return True
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接（不断开浏览器，只清理本地连接）"""
        try:
            if self._page:
                self._page.close()
                self._page = None
            # 注意：不关闭 browser，只断开 CDP 连接
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception:
            pass
        finally:
            self._page = None
            self._browser = None
            self._playwright = None

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._page is not None

    def navigate_to_home(self) -> bool:
        """导航到 DO+ 首页"""
        if not self._page:
            return False
        try:
            self._page.goto(self.DO_PLUS_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 导航失败: {e}")
            return False

    def navigate_to_promote_list(self) -> bool:
        """导航到推广列表页面"""
        if not self._page:
            return False
        try:
            self._page.goto(self.DO_PLUS_PROMOTE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 导航到推广列表失败: {e}")
            return False

    def check_login_status(self) -> dict:
        """检查登录状态"""
        if not self._page:
            return {"logged_in": False, "message": "未连接"}

        try:
            page_text = self._page.inner_text("body")
            risk_indicators = ["验证码", "二维码", "登录", "授权", "验证", "手机"]

            for indicator in risk_indicators:
                if indicator in page_text:
                    return {"logged_in": False, "message": f"页面包含: {indicator}", "risk": True}

            if "退出" in page_text or "我的" in page_text or "创作中心" in page_text:
                return {"logged_in": True, "message": "已登录"}

            return {"logged_in": False, "message": "未检测到登录状态"}
        except Exception as e:
            return {"logged_in": False, "message": f"检查失败: {e}"}

    def _check_risk(self) -> list:
        """检查页面风险"""
        try:
            page_text = self._page.inner_text("body")
            risk_indicators = ["验证码", "二维码", "登录", "授权", "验证", "手机", "实名"]
            found = [ind for ind in risk_indicators if ind in page_text]
            return found
        except Exception:
            return []

    def get_campaign_list(self) -> list:
        """获取推广计划列表"""
        if not self._page:
            return []

        try:
            time.sleep(2)
            campaigns = []
            rows = self._page.query_selector_all("[role='row'], tr, .campaign-item, .promo-item")
            for row in rows:
                row_text = row.inner_text()
                if "加热" in row_text or "推广" in row_text or "投放" in row_text:
                    campaign = {
                        "name": self._extract_campaign_name(row_text),
                        "status": self._parse_status(row_text),
                        "budget": self._extract_budget(row_text),
                    }
                    id_match = re.search(r'ID:(\d+)', row_text)
                    if id_match:
                        campaign["id"] = id_match.group(1)
                    campaigns.append(campaign)

            return campaigns
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 获取推广列表失败: {e}")
            return []

    def _extract_campaign_name(self, text: str) -> str:
        """提取推广名称"""
        match = re.search(r'(内容加热[^\s]+|推广[^\s]+)', text)
        return match.group(1) if match else ""

    def _parse_status(self, text: str) -> str:
        """解析推广状态"""
        if "投放中" in text or "进行" in text:
            return "投放中"
        elif "暂停" in text:
            return "暂停"
        elif "已结束" in text or "结束" in text:
            return "已结束"
        return "未知"

    def _extract_budget(self, text: str) -> str:
        """提取预算"""
        match = re.search(r'预算[：:]*\s*(\d+\.?\d*)\s*元?', text)
        return match.group(1) if match else ""

    def create_content_heating(self, video_id: str, config: dict) -> dict:
        """创建内容加热推广

        Args:
            video_id: 视频 ID
            config: 推广配置，包含:
                - budget: 日预算
                - duration: 推广天数
                - target_type: 目标类型（播放/互动）

        Returns:
            dict: 包含 success, campaign_id, message
        """
        if not self._page:
            return {"success": False, "message": "未连接浏览器"}

        try:
            risk = self._check_risk()
            if risk:
                return {"success": False, "message": f"页面存在风险: {risk}"}

            # 导航到创建页面
            create_url = f"{self.DO_PLUS_HOME_URL}/promo/create?video_id={video_id}"
            self._page.goto(create_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            self._fill_heating_form(config)

            if not self._validate_campaign(config):
                return {"success": False, "message": "推广验证失败"}

            self._click_publish()

            time.sleep(5)

            campaign_id = self._extract_campaign_id(video_id)
            if not campaign_id:
                return {"success": False, "message": "未能获取推广 ID"}

            return {
                "success": True,
                "campaign_id": campaign_id,
                "message": "推广创建成功"
            }

        except Exception as e:
            return {"success": False, "message": f"创建失败: {e}"}

    def _fill_heating_form(self, config: dict):
        """填写推广表单"""
        # 预算输入
        budget_input = self._page.query_selector('input[placeholder*="预算"], input[placeholder*="日预算"]')
        if budget_input:
            self._set_input_value(budget_input, str(config.get("budget", "100")))

        time.sleep(0.5)

        # 时长选择
        duration = config.get("duration", 7)
        duration_btns = self._page.query_selector_all("button, .duration-option")
        for btn in duration_btns:
            if f"{duration}天" in btn.inner_text() or f"{duration}天" in str(btn.get_attribute("data-duration")):
                btn.click()
                break

    def _set_input_value(self, element, value: str):
        """设置输入框的值（触发响应式）"""
        self._page.evaluate("""
            (el, val) => {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, val);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """, element, value)

    def _validate_campaign(self, config: dict) -> bool:
        """验证推广表单"""
        try:
            page_text = self._page.inner_text("body")

            if "预算" in page_text and config.get("budget"):
                budget = str(config.get("budget"))
                if budget not in page_text:
                    print(f"[DouyinPlusBrowserOps] 预算未设置: {budget}")
                    return False

            return True
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 验证失败: {e}")
            return False

    def _click_publish(self):
        """点击发布推广"""
        try:
            buttons = self._page.query_selector_all("button")
            for btn in buttons:
                btn_text = btn.inner_text()
                if "发布" in btn_text or "开始推广" in btn_text or "确认" in btn_text:
                    btn.click()
                    return True
            return False
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 点击发布失败: {e}")
            return False

    def _extract_campaign_id(self, video_id: str) -> Optional[str]:
        """从页面提取推广 ID"""
        try:
            time.sleep(2)
            page_text = self._page.inner_text("body")

            id_match = re.search(r'推广[ID：:]*(\d+)', page_text)
            if id_match:
                return id_match.group(1)

            id_match = re.search(r'ID:(\d{10,})', page_text)
            if id_match:
                return id_match.group(1)

            return None
        except Exception:
            return None

    def pause_campaign(self, campaign_id: str) -> bool:
        """暂停推广"""
        return self._set_campaign_status(campaign_id, "pause")

    def resume_campaign(self, campaign_id: str) -> bool:
        """恢复推广"""
        return self._set_campaign_status(campaign_id, "resume")

    def delete_campaign(self, campaign_id: str) -> bool:
        """删除推广"""
        if not self._page:
            return False

        try:
            self.navigate_to_promote_list()
            time.sleep(2)

            row = self._find_campaign_row(campaign_id)
            if not row:
                return False

            buttons = row.query_selector_all("button")
            for btn in buttons:
                if "删除" in btn.inner_text():
                    btn.click()
                    time.sleep(1)
                    confirm_btn = self._page.query_selector("button:has-text('确认'), button:has-text('确定')")
                    if confirm_btn:
                        confirm_btn.click()
                    return True

            return False
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 删除失败: {e}")
            return False

    def _set_campaign_status(self, campaign_id: str, action: str) -> bool:
        """设置推广状态"""
        if not self._page:
            return False

        try:
            self.navigate_to_promote_list()
            time.sleep(2)

            row = self._find_campaign_row(campaign_id)
            if not row:
                print(f"[DouyinPlusBrowserOps] 未找到推广: {campaign_id}")
                return False

            action_text = "暂停" if action == "pause" else "开启"
            buttons = row.query_selector_all("button")
            for btn in buttons:
                if action_text in btn.inner_text():
                    btn.click()
                    time.sleep(1)
                    return True

            return False
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 设置状态失败: {e}")
            return False

    def _find_campaign_row(self, campaign_id: str):
        """查找推广所在的行"""
        try:
            rows = self._page.query_selector_all("[role='row'], tr, .campaign-item, .promo-item")
            for row in rows:
                if campaign_id in row.inner_text():
                    return row
            return None
        except Exception:
            return None

    def get_metrics(self, campaign_id: str) -> dict:
        """获取推广数据指标"""
        if not self._page:
            return {}

        try:
            self.navigate_to_promote_list()
            time.sleep(2)

            row = self._find_campaign_row(campaign_id)
            if not row:
                return {}

            row_text = row.inner_text()

            metrics = {
                "plays": self._extract_number(row_text, ["播放", "观看", "曝光"]),
                "likes": self._extract_number(row_text, ["点赞", "喜欢"]),
                "comments": self._extract_number(row_text, ["评论", "留言"]),
                "shares": self._extract_number(row_text, ["转发", "分享"]),
                "spend": self._extract_money(row_text),
            }

            return metrics
        except Exception as e:
            print(f"[DouyinPlusBrowserOps] 获取指标失败: {e}")
            return {}

    def _extract_number(self, text: str, keywords: list) -> int:
        """提取数字"""
        for kw in keywords:
            pattern = rf'{kw}[：:]*\s*(\d+)'
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return 0

    def _extract_money(self, text: str) -> float:
        """提取金额"""
        patterns = [
            r'¥\s*([\d.]+)',
            r'￥\s*([\d.]+)',
            r'消耗[：:]*\s*([\d.]+)',
            r'花费[：:]*\s*([\d.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return 0.0