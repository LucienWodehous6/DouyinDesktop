"""巨量千川浏览器自动化操作"""
import time
import json
import re
from typing import Optional


class JuliangBrowserOps:
    """巨量千川浏览器操作类 — 通过 Playwright CDP 操作巨量千川后台"""

    # 巨量千川 URL
    QC_HOME_URL = "https://qianchuan.jinritemai.com/"
    QC_LIVE_HEATING_URL = "https://qianchuan.jinritemai.com/brand_bid/brand/live_heating"

    def __init__(self, cdp_url: str):
        self.cdp_url = cdp_url
        self._page = None
        self._browser = None
        self._playwright = None

    def connect(self) -> bool:
        """连接到浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            print(f"[JuliangBrowserOps] 正在连接到 CDP: {self.cdp_url}")
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)
            print(f"[JuliangBrowserOps] 浏览器已连接，目标: {self._browser}")

            # 创建新页面用于操作
            context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
            self._page = context.new_page()
            print(f"[JuliangBrowserOps] 新页面已创建: {self._page}")
            return True
        except Exception as e:
            print(f"[JuliangBrowserOps] 连接失败: {e}")
            import traceback
            traceback.print_exc()
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
        except Exception as e:
            print(f"[JuliangBrowserOps] 断开连接时出错: {e}")
        finally:
            self._page = None
            self._browser = None
            self._playwright = None

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._page is not None

    def navigate_to_home(self) -> bool:
        """导航到巨量千川首页"""
        if not self._page:
            print("[JuliangBrowserOps] 未连接页面")
            return False
        try:
            print(f"[JuliangBrowserOps] 导航到: {self.QC_HOME_URL}")
            self._page.goto(self.QC_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            print(f"[JuliangBrowserOps] 当前URL: {self._page.url}")
            return True
        except Exception as e:
            print(f"[JuliangBrowserOps] 导航失败: {e}")
            return False

    def navigate_to_live_heating(self) -> bool:
        """导航到直播加热页面"""
        if not self._page:
            print("[JuliangBrowserOps] 未连接页面")
            return False
        try:
            print(f"[JuliangBrowserOps] 导航到: {self.QC_LIVE_HEATING_URL}")
            self._page.goto(self.QC_LIVE_HEATING_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            print(f"[JuliangBrowserOps] 当前URL: {self._page.url}")
            return True
        except Exception as e:
            print(f"[JuliangBrowserOps] 导航到直播加热失败: {e}")
            return False

    def check_login_status(self) -> dict:
        """检查登录状态"""
        if not self._page:
            return {"logged_in": False, "message": "未连接"}

        try:
            page_text = self._page.inner_text("body")
            risk_indicators = ["验证码", "二维码", "登录", "授权", "扣费确认", "协议确认", "风控", "资质", "违规", "权限"]

            for indicator in risk_indicators:
                if indicator in page_text:
                    return {"logged_in": False, "message": f"页面包含: {indicator}", "risk": True}

            if "退出" in page_text or "账户" in page_text or "广告主" in page_text:
                return {"logged_in": True, "message": "已登录"}

            return {"logged_in": False, "message": "未检测到登录状态"}
        except Exception as e:
            return {"logged_in": False, "message": f"检查失败: {e}"}

    def get_plan_list(self) -> list:
        """获取计划列表"""
        if not self._page:
            print("[JuliangBrowserOps] get_plan_list: 未连接页面")
            return []

        try:
            print("[JuliangBrowserOps] 正在获取计划列表...")
            time.sleep(2)
            plans = []
            rows = self._page.query_selector_all("[role='row'], tr")
            print(f"[JuliangBrowserOps] 找到 {len(rows)} 行")
            for row in rows:
                row_text = row.inner_text()
                if "直播加热_行为" in row_text:
                    plan = {
                        "name": self._extract_plan_name(row_text),
                        "status": self._parse_status(row_text),
                        "bid": self._extract_bid(row_text),
                    }
                    id_match = re.search(r'ID:(\d+)', row_text)
                    if id_match:
                        plan["id"] = id_match.group(1)
                    plans.append(plan)
                    print(f"[JuliangBrowserOps] 发现计划: {plan}")

            return plans
        except Exception as e:
            print(f"[JuliangBrowserOps] 获取计划列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_plan_name(self, text: str) -> str:
        """提取计划名称"""
        match = re.search(r'(直播加热_行为[^\s]+)', text)
        return match.group(1) if match else ""

    def _parse_status(self, text: str) -> str:
        """解析计划状态"""
        if "投放中" in text or "运行" in text:
            return "投放中"
        elif "暂停" in text:
            return "暂停"
        elif "已结束" in text or "结束" in text:
            return "已结束"
        return "未知"

    def _extract_bid(self, text: str) -> str:
        """提取出价"""
        match = re.search(r'(\d+\.?\d*)\s*元?', text)
        return match.group(1) if match else ""

    def create_plan(self, plan_config: dict) -> dict:
        """创建投放计划"""
        if not self._page:
            return {"success": False, "message": "未连接浏览器"}

        try:
            print(f"[JuliangBrowserOps] 开始创建计划: {plan_config}")
            risk = self._check_risk()
            if risk:
                print(f"[JuliangBrowserOps] 页面存在风险: {risk}")
                return {"success": False, "message": f"页面存在风险: {risk}"}

            create_url = f"{self.QC_HOME_URL}brand_bid/creation/feed-live-heating"
            print(f"[JuliangBrowserOps] 导航到创建页: {create_url}")
            self._page.goto(create_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            self._fill_plan_form(plan_config)

            if not self._validate_plan(plan_config):
                return {"success": False, "message": "计划验证失败"}

            self._click_publish()

            time.sleep(5)

            plan_id = self._extract_plan_id(plan_config.get("name", ""))
            if not plan_id:
                return {"success": False, "message": "未能获取计划 ID"}

            return {
                "success": True,
                "plan_id": plan_id,
                "message": "计划创建成功"
            }

        except Exception as e:
            print(f"[JuliangBrowserOps] 创建失败: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"创建失败: {e}"}

    def _check_risk(self) -> list:
        """检查页面风险"""
        try:
            page_text = self._page.inner_text("body")
            risk_indicators = ["验证码", "二维码", "登录", "授权", "扣费确认", "协议确认", "风控", "资质", "违规", "权限"]
            found = [ind for ind in risk_indicators if ind in page_text]
            return found
        except Exception:
            return []

    def _fill_plan_form(self, config: dict):
        """填写计划表单"""
        print("[JuliangBrowserOps] 填写表单...")
        bid_input = self._page.query_selector('input[placeholder="请输入价格"]')
        if bid_input:
            print(f"[JuliangBrowserOps] 找到出价输入框，设置值: {config.get('bid', '0.22')}")
            self._set_input_value(bid_input, str(config.get("bid", "0.22")))
        else:
            print("[JuliangBrowserOps] 未找到出价输入框")

        time.sleep(0.5)

        name_input = self._page.query_selector('input[placeholder="请输入计划名称，1-50个字符"]')
        if name_input:
            plan_name = config.get("name", f"直播加热_行为{config.get('behavior')}_兴趣{config.get('interest')}")
            print(f"[JuliangBrowserOps] 找到名称输入框，设置值: {plan_name}")
            self._set_input_value(name_input, plan_name)
        else:
            print("[JuliangBrowserOps] 未找到名称输入框")

        time.sleep(0.5)

        group_input = self._page.query_selector('input[placeholder="请选择广告组"]')
        if group_input:
            print("[JuliangBrowserOps] 找到广告组输入框，点击...")
            group_input.click()
            time.sleep(0.5)
            target_group = config.get("target_group", "")
            option = self._page.query_selector(f'text="{target_group}"')
            if option:
                option.click()

    def _set_input_value(self, element, value: str):
        """设置输入框的值（触发 Vue 响应式）"""
        try:
            self._page.evaluate("""
                (el, val) => {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(el, val);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, element, value)
        except Exception as e:
            print(f"[JuliangBrowserOps] 设置输入框值失败: {e}")

    def _validate_plan(self, config: dict) -> bool:
        """验证计划表单"""
        try:
            page_text = self._page.inner_text("body")

            if "计划名称重复" in page_text:
                print("[JuliangBrowserOps] 计划名称重复")
                return False

            required = [
                ("行为", config.get("behavior", "")),
                ("兴趣", config.get("interest", "")),
            ]

            for label, value in required:
                if value and value not in page_text:
                    print(f"[JuliangBrowserOps] 缺少 {label}: {value}")
                    return False

            return True
        except Exception as e:
            print(f"[JuliangBrowserOps] 验证失败: {e}")
            return False

    def _click_publish(self):
        """点击发布计划"""
        try:
            buttons = self._page.query_selector_all("button")
            for btn in buttons:
                if "发布计划" in btn.inner_text():
                    print("[JuliangBrowserOps] 点击发布计划按钮")
                    btn.click()
                    return True
            print("[JuliangBrowserOps] 未找到发布计划按钮")
            return False
        except Exception as e:
            print(f"[JuliangBrowserOps] 点击发布失败: {e}")
            return False

    def _extract_plan_id(self, plan_name: str) -> Optional[str]:
        """从页面提取计划 ID"""
        try:
            time.sleep(2)
            page_text = self._page.inner_text("body")

            if plan_name in page_text:
                pattern = rf'{re.escape(plan_name)}[\s\S]*?ID:(\d+)'
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1)

                id_match = re.search(r'ID:(\d{10,})', page_text)
                if id_match:
                    return id_match.group(1)

            return None
        except Exception:
            return None

    def pause_plan(self, plan_id: str) -> bool:
        """暂停计划"""
        return self._set_plan_status(plan_id, "pause")

    def resume_plan(self, plan_id: str) -> bool:
        """恢复计划"""
        return self._set_plan_status(plan_id, "resume")

    def _set_plan_status(self, plan_id: str, action: str) -> bool:
        """设置计划状态"""
        if not self._page:
            return False

        try:
            self.navigate_to_live_heating()
            time.sleep(2)

            row = self._find_plan_row(plan_id)
            if not row:
                print(f"[JuliangBrowserOps] 未找到计划: {plan_id}")
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
            print(f"[JuliangBrowserOps] 设置状态失败: {e}")
            return False

    def _find_plan_row(self, plan_id: str):
        """查找计划所在的行"""
        try:
            rows = self._page.query_selector_all("[role='row'], tr")
            for row in rows:
                if plan_id in row.inner_text():
                    return row
            return None
        except Exception:
            return None

    def delete_plan(self, plan_id: str) -> bool:
        """删除计划"""
        if not self._page:
            return False

        try:
            self.navigate_to_live_heating()
            time.sleep(2)

            row = self._find_plan_row(plan_id)
            if not row:
                return False

            buttons = row.query_selector_all("button")
            for btn in buttons:
                if "删除" in btn.inner_text():
                    btn.click()
                    time.sleep(1)
                    confirm_btn = self._page.query_selector("button:has-text('确认')")
                    if confirm_btn:
                        confirm_btn.click()
                    return True

            return False
        except Exception as e:
            print(f"[JuliangBrowserOps] 删除失败: {e}")
            return False

    def get_plan_metrics(self, plan_id: str) -> dict:
        """获取计划指标"""
        if not self._page:
            return {}

        try:
            self.navigate_to_live_heating()
            time.sleep(2)

            row = self._find_plan_row(plan_id)
            if not row:
                return {}

            row_text = row.inner_text()

            metrics = {
                "plays": self._extract_number(row_text, ["播放", "观看"]),
                "interactions": self._extract_number(row_text, ["互动", "评论", "点赞"]),
                "spend": self._extract_money(row_text),
            }

            return metrics
        except Exception as e:
            print(f"[JuliangBrowserOps] 获取指标失败: {e}")
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
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return 0.0