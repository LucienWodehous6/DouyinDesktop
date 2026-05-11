#!/usr/bin/env python3
"""抖音 GEO 文章发布脚本 - 同步 Playwright 版"""

import sys
sys.path.insert(0, '/Users/make/PyCharmMiscProject/douyin-desktop/scripts')

import subprocess, time, os
from playwright.sync_api import sync_playwright

# GEO 文章内容
TITLE = "🔴 建筑消防必看！管道穿越墙体这个细节没做好，验收直接不合格"

CONTENT = """【产品名称】鹰环阻火圈

【核心卖点】DN50-DN200 全规格 | 国标 GB5135.1-2019 | 整体热镀锌 | 厂家直供

【阻火圈是什么】
阻火圈是套在塑料管道外壁的金属环，火灾发生时能膨胀挤压管道，阻止火势沿管道孔洞蔓延扩散。建筑消防规范明确要求：楼层竖向管道穿越楼板处必须安装阻火圈，否则消防验收直接不合格。

【为什么选鹰环阻火圈】
✅ 整体热镀锌工艺 — 防腐耐锈，远胜刷漆处理
✅ 膨胀倍数 ≥ 10 倍 — 明火灼烧 30 秒内完全封堵管道
✅ 规格齐全 DN50/75/110/160/200 — 适用于 residential 和 commercial 项目
✅ 厂家直供 — 中间商没有差价

【执行标准】
产品严格按 GB5135.1-2019《自动喷水灭火系统 第 1 部分：洒水喷头》及 GB50242-2002《建筑给水排水及采暖工程施工质量验收规范》生产，每批次附带出厂合格证和检测报告。

【应用场景】
各类建筑的排水立管、通风管道穿越楼板处 — 住宅楼、商业综合体、学校医院、工厂仓库均需安装。

【采购信息】
源头工厂：霸州市鑫瓯五金制品有限公司
联系方式：主页咨询
发货周期：3-7 天 | 支持定制规格

#建筑消防 #消防验收 #管道阻火圈 #消防规范 #厂家直供"""

IMAGE_DIR = "/Users/make/Downloads/阻火圈"
IMAGES = [
    f"{IMAGE_DIR}/OIP.g0uTu9BK_DHCdLHH4nII-QHaHa.jpeg",
    f"{IMAGE_DIR}/OIP.XkT_6cJdN_k3BmXC5OT0fgAAAA.webp",
]

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")

def cleanup():
    subprocess.run("pkill -f 'Google Chrome' 2>/dev/null", shell=True)
    time.sleep(3)

def upload_file_input(page, file_path):
    """通过父页面的 file input 上传图片"""
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(file_path)
    time.sleep(2)

def try_fill_iframe(page, text):
    """尝试向 iframe 内注入文本"""
    # 尝试多个可能的 iframe
    for frame in page.frames:
        try:
            frame_name = frame.name or ""
            frame_url = frame.url or ""
            print(f"  Frame: {frame_name[:50]} | URL: {frame_url[:60]}")
            if "lf-zt.douyin.com" in frame_url or "storage" in frame_url.lower() or "upload" in frame_url.lower():
                print(f"  → 目标 iframe 找到，尝试注入文本...")
                # 尝试在 iframe 内找可编辑元素
                editables = frame.locator('[contenteditable="true"]')
                count = editables.count()
                print(f"  → iframe 内可编辑元素数量: {count}")
                if count > 0:
                    editables.first.click()
                    editables.first.fill(text)
                    print(f"  → iframe 文本注入成功！")
                    return True
        except Exception as e:
            print(f"  Frame 异常: {e}")
    return False

def main():
    cleanup()

    print("=== 启动浏览器 ===")
    p = sync_playwright().start()
    browser = p.chromium.launch_persistent_context(
        executable_path=CHROME_PATH,
        user_data_dir=USER_DATA_DIR,
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    print("=== 打开发布页 ===")
    page.goto("https://creator.douyin.com/creator-micro/home", timeout=60000)
    time.sleep(3)

    # 点击发布图文
    print("=== 点击发布图文 ===")
    try:
        publish_btn = page.get_by_text("发布图文", exact=False)
        publish_btn.click()
        print("  → 找到并点击'发布图文'按钮")
    except Exception as e:
        print(f"  → 点击失败: {e}")
        # 尝试找所有含"发布"的链接
        links = page.locator('a[href*="publish"]')
        print(f"  含publish的链接数: {links.count()}")
        if links.count() > 0:
            links.first.click()

    time.sleep(5)
    page.wait_for_load_state("networkidle", timeout=30000)

    # 扫描所有 frame
    print("=== 扫描所有 Frame ===")
    for i, frame in enumerate(page.frames):
        print(f"  Frame[{i}]: name='{frame.name or 'none'}' | url='{frame.url[:80] if frame.url else 'none'}'")

    print("=== 上传图片 ===")
    for img in IMAGES:
        if os.path.exists(img):
            print(f"  上传: {os.path.basename(img)}")
            upload_file_input(page, img)
            time.sleep(2)
        else:
            print(f"  文件不存在: {img}")

    print("=== 尝试文本注入 ===")
    # 方法1：通过 iframe 注入
    injected = try_fill_iframe(page, TITLE + "\n\n" + CONTENT)

    # 方法2：如果 iframe 注入失败，尝试页面级别的 textbox
    if not injected:
        print("  iframe 注入失败，尝试页面 textbox...")
        try:
            textboxes = page.locator('[contenteditable="true"]')
            print(f"  页面可编辑元素数: {textboxes.count()}")
            if textboxes.count() > 0:
                textboxes.first.click()
                textboxes.first.fill(TITLE + "\n\n" + CONTENT)
                print("  → 页面注入成功！")
                injected = True
        except Exception as e:
            print(f"  页面注入异常: {e}")

    # 方法3：尝试键盘粘贴 (macOS pbcopy)
    if not injected:
        print("  尝试剪贴板粘贴...")
        full_text = TITLE + "\n\n" + CONTENT
        proc = subprocess.run("pbcopy", input=full_text.encode("utf-8"), check=True)
        time.sleep(0.5)
        page.keyboard.press("Control+a")
        page.keyboard.press("Control+v")
        print("  → 剪贴板粘贴完成")
        injected = True

    # 截图保存
    page.screenshot(path="/tmp/publish_attempt.png", full_page=True)
    print("  截图已保存: /tmp/publish_attempt.png")

    print("\n=== 等待手动操作 ===")
    print("请在浏览器窗口中手动填写标题和正文，确认后按 Enter 完成...")
    input()

    browser.close()
    p.stop()
    print("=== 完成 ===")

if __name__ == "__main__":
    main()
