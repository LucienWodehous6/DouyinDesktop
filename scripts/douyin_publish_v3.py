#!/usr/bin/env python3
"""
抖音图文发布 - 使用 CDP 直接操作文件选择对话框
绕过 Playwright 的 file chooser 限制
"""
import asyncio
import json
import subprocess
from pathlib import Path

TITLE = "霸州这家阻火圈厂家，火了！建筑消防管道都在用"
CONTENT = """🔥 在河北霸州，有一家专注阻火圈生产的厂家——霸州市鑫瓯五金制品有限公司。

🏭 我们是谁？
专业生产建筑消防管道配套阻火圈，规格齐全（DN50-DN200），广泛应用于楼宇、商场、医院、学校等消防管道系统。

✅ 为什么选择我们？
▪ 源头工厂，价格实惠
▪ 质量可靠，符合国家标准
▪ 交货及时，售后有保障
▪ 支持定制，量大从优

🏗️ 我们的客户
建筑承包商、消防工程公司、建材经销商……都已建立长期合作。

📞 有需要的朋友，直接联系！
霸州市鑫瓯五金制品有限公司
京津冀地区可送货上门

#阻火圈 #消防器材 #河北厂家 #五金制品 #建筑消防 #管道配件 #霸州 #廊坊"""

IMAGES = [
    "/Users/make/Downloads/阻火圈/OIP.g0uTu9BK_DHCdLHH4nII-QHaHa.jpeg",
    "/Users/make/Downloads/阻火圈/OIP.XkT_6cJdN_k3BmXC5OT0fgAAAA.webp"
]

def run_script(js_code):
    """通过 macOS osascript 执行 JavaScript"""
    script = f'''
    tell application "Google Chrome for Testing"
        activate
    end tell
    '''
    return subprocess.run(['osascript', '-e', script], capture_output=True, text=True)

async def main():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            executable_path='/Users/make/PyCharmMiscProject/douyin-desktop/playwright_browsers/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
            headless=False,
            user_data_dir='/tmp/chrome-douyin-publish',
            args=["--disable-blink-features=AutomationControlled"],
        )
        
        # 注入 Cookie
        COOKIE_STR = "sid_tt=b7ef9bb9e28b14dcf3fee493e6b88555; sessionid=b7ef9bb9e28b14dcf3fee493e6b88555; uid_tt=49b9a260bc17d8218f411d041f3b672e; ttwid=1%7Cv2HqEFxRWcXDZWsj6A_67hLGjacnlY73jGiJ13RQVRU%7C1778469789%7C3ec16b571db0550ce2ade425fc3b6a8b7d372c9c5f8da9403dd3d95d253c080e; __ac_nonce=06a014b99003613b7cb00; __ac_signature=_02B4Z6wo00f01mlKh2wAAIDDZ-zkaOE2qzJpaoPAAPBieb"
        for part in COOKIE_STR.split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                await browser.add_cookies([{
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".douyin.com",
                    "path": "/"
                }])
        print("Cookie 注入完成")
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        print("打开创作者中心...")
        await page.goto("https://creator.douyin.com/creator-micro/home", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)
        
        # 检查是否登录
        url = page.url
        if "login" in url.lower():
            print("需要登录，请在浏览器中扫码...")
            await page.screenshot(path="/tmp/need_login.png")
            await asyncio.Event().wait()
            return
        
        print(f"已登录，当前 URL: {url}")
        await page.screenshot(path="/tmp/step1_home.png")
        
        # 点击发布图文
        print("点击发布图文...")
        try:
            await page.locator("text=发布图文").first.click(timeout=5000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"点击失败: {e}")
        
        await page.screenshot(path="/tmp/step2_upload_page.png")
        print("上传页面已打开")
        
        # 监听文件选择对话框
        def handle_file_chooser(chooser):
            print(f"文件选择对话框打开，模式: {chooser.mode}")
            # 设置文件
            chooser.set_files(IMAGES)
            print(f"已设置文件: {IMAGES}")
        
        page.on("filechooser", handle_file_chooser)
        
        # 查找并点击"选择文件"按钮
        print("查找选择文件按钮...")
        
        # 方法1: 点击"选择文件"按钮
        try:
            btn = page.locator("button:has-text('选择文件')").first
            if await btn.count() > 0:
                print("找到选择文件按钮，点击...")
                await btn.click(timeout=3000)
                await asyncio.sleep(2)
        except Exception as e:
            print(f"方法1失败: {e}")
        
        # 方法2: 找到 file input 并上传
        try:
            file_input = page.locator('input[type="file"]').first
            if await file_input.count() > 0:
                print("找到 file input，直接上传...")
                await file_input.set_input_files(IMAGES)
                print("文件上传成功")
        except Exception as e:
            print(f"方法2失败: {e}")
        
        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/step3_after_upload.png")
        
        # 尝试填写标题和正文（如果出现在主页面）
        print("尝试填写标题...")
        
        # 切换到所有 frame 并查找元素
        for frame in page.frames:
            try:
                frame_name = frame.name or frame.url
                print(f"检查 frame: {frame_name[:60]}")
                
                # 尝试查找标题输入框
                try:
                    title_el = await frame.query_selector('input.semi-input')
                    if title_el:
                        print(f"在 frame {frame_name[:40]} 中找到标题输入框!")
                        await title_el.fill(TITLE)
                        print("标题已填写")
                except:
                    pass
                
                # 尝试查找正文编辑框
                try:
                    editor_el = await frame.query_selector('[contenteditable="true"][data-placeholder*="描述"]')
                    if editor_el:
                        print(f"在 frame {frame_name[:40]} 中找到正文编辑框!")
                        await editor_el.fill(CONTENT)
                        print("正文已填写")
                except:
                    pass
                    
            except Exception as e:
                print(f"frame {frame_name[:40]} 访问失败: {e}")
        
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/step4_final.png")
        
        print("流程完成，浏览器保持打开...")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())