# 内容创作增强 — SEO 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在剧本生成完成后自动触发 SEO 优化，展示优化后的剧本

**Architecture:** 新增 `SEOOptimizeWorker` QThread 处理第二次 AI 调用，修改 `ScriptPanel._on_result()` 在剧本生成后自动触发 SEO 优化，SEO 结果通过 `_on_seo_result()` 展示到 result_label

**Tech Stack:** PyQt6 QThread, 复用现有 OpenAI API 配置

---

## 文件结构

```
app/widgets/script_panel.py     # 修改：_on_result、_run_seo_optimize、_on_seo_result
```

---

### Task 1: 创建 SEOOptimizeWorker

**Files:**
- Modify: `app/widgets/script_panel.py`（在文件末尾添加新类）

- [ ] **Step 1: 在 script_panel.py 末尾添加 SEOOptimizeWorker**

Read the end of `app/widgets/script_panel.py` first, then add before the final `def _refresh_tasks(self):` or at the end of the file.

```python
class SEOOptimizeWorker(QThread):
    """SEO 优化后台线程 — 对已生成的剧本进行标题和标签优化"""

    chunk_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, script_text: str, topic: str, api_key: str,
                 api_base: str, model: str):
        super().__init__()
        self.script_text = script_text
        self.topic = topic
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def run(self):
        try:
            from openai import OpenAI

            base_url = self.api_base.rstrip("/")
            client = OpenAI(api_key=self.api_key, base_url=base_url)

            prompt = f"""你是一位抖音 SEO 优化专家。请对以下剧本进行标题和标签优化。

原始剧本：
{self.script_text}

任务要求：
1. 优化标题（≤20字，吸睛，包含关键词）
2. 生成 2 个变体标题（信任型、紧迫型）
3. 推荐 5 个标签（以 # 开头，符合抖音平台规范）
4. 生成视频描述（≤100字）
5. 优化剧本正文（保留原有结构，只优化标题和话术表达）

请严格按以下格式输出：

【优化标题】
（标题内容，≤20字）

【标题变体】
变体A（信任型）：xxx
变体B（紧迫型）：xxx

【推荐标签】
#标签1 #标签2 #标签3 #标签4 #标签5

【视频描述】
（描述内容，≤100字）

【优化后剧本】
（将优化后的完整剧本输出，保留原有结构）
"""

            messages = [{"role": "user", "content": prompt}]

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                stream=True,
            )

            full_content = ""
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                text = delta.content or ""
                if text:
                    full_content += text
                    self.chunk_signal.emit(text)

            self.result_signal.emit(full_content)

        except Exception as e:
            self.error_signal.emit(str(e))
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/script_panel.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add app/widgets/script_panel.py
git commit -m "feat(script): add SEOOptimizeWorker for script SEO optimization"
```

---

### Task 2: 修改 _on_result 触发自动 SEO 优化

**Files:**
- Modify: `app/widgets/script_panel.py`（修改 `_on_result` 方法）

- [ ] **Step 1: 读取并修改 _on_result 方法**

Read the `_on_result` method (around line 578) in `app/widgets/script_panel.py`. Replace the entire `_on_result` method with:

```python
    def _on_result(self, text: str):
        print(f"[剧本] === 生成完成 === ({len(text)} 字符)")
        self._last_result = text
        self._last_prompt = self.prompt_edit.toPlainText().strip()
        self._hide_progress()

        # 自动触发 SEO 优化（不立即展示原剧本）
        topic = self.prompt_edit.toPlainText().strip()[:50]
        self._run_seo_optimize(text, topic)
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/make/PyCharmMiscProject/douyin-desktop && python3 -m py_compile app/widgets/script_panel.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add app/widgets/script_panel.py
git commit -m "feat(script): trigger SEO optimization after script generation"
```

---

### Task 3: 添加 _run_seo_optimize 方法

**Files:**
- Modify: `app/widgets/script_panel.py`（在 `_on_result` 后添加新方法）

- [ ] **Step 1: 在 `_on_result` 方法后添加 `_run_seo_optimize` 方法**

Read `app/widgets/script_panel.py` around line 588 to find where to insert. Add after `_on_result` ends:

```python
    def _run_seo_optimize(self, script_text: str, topic: str):
        """触发 SEO 优化流程"""
        api_key = self._settings.get("openai_text_api_key") or self._settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
        api_base = self._settings.get("openai_text_api_base") or self._settings.get("openai_api_base") or os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1")
        model = self._settings.get("openai_text_model") or self._settings.get("openai_model") or os.environ.get("OPENAI_MODEL", "deepseek-chat")

        if not api_key:
            # 无 API key，直接显示原剧本
            self._show_final_result(script_text)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在优化 SEO...")
        self.result_label.setText("AI 正在优化标题和标签，请稍候...")
        self.gen_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.modify_btn.setEnabled(False)

        self._worker = SEOOptimizeWorker(
            script_text=script_text,
            topic=topic,
            api_key=api_key,
            api_base=api_base,
            model=model,
        )
        self._worker.chunk_signal.connect(self._on_seo_chunk)
        self._worker.result_signal.connect(self._on_seo_result)
        self._worker.error_signal.connect(self._on_seo_error)
        self._worker.start()
```

- [ ] **Step 2: 验证语法**

Run: `python3 -m py_compile app/widgets/script_panel.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/script_panel.py
git commit -m "feat(script): add _run_seo_optimize method"
```

---

### Task 4: 添加 SEO 结果处理方法

**Files:**
- Modify: `app/widgets/script_panel.py`

- [ ] **Step 1: 添加 `_on_seo_chunk`、`_on_seo_result`、`_on_seo_error` 方法**

在 `_run_seo_optimize` 方法后添加：

```python
    def _on_seo_chunk(self, text: str):
        """SEO 优化流式追加"""
        if not hasattr(self, "_seo_result_buf"):
            self._seo_result_buf = ""
        self._seo_result_buf += text
        html = self._render_markdown(self._seo_result_buf)
        self.result_label.setText(html)
        self.result_scroll.verticalScrollBar().setValue(
            self.result_scroll.verticalScrollBar().maximum()
        )

    def _on_seo_result(self, text: str):
        """SEO 优化完成"""
        print(f"[剧本] === SEO 优化完成 === ({len(text)} 字符)")
        self._last_result = text
        self._hide_progress()
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)
        self.gen_btn.setText("✨ AI 生成剧本")
        # 直接显示优化后结果
        self._show_final_result(text)

    def _on_seo_error(self, msg: str):
        """SEO 优化失败，回退到原剧本"""
        print(f"[剧本] === SEO 优化失败 === {msg}")
        self._hide_progress()
        self.result_label.setText(
            f"<p style='color:#f85149'>⚠️ SEO 优化失败，显示原始剧本：</p>"
            f"<pre style='color:#c9d1d9'>{self._last_result[:500]}</pre>"
        )
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)

    def _show_final_result(self, text: str):
        """展示最终结果（渲染 markdown）"""
        html = self._render_markdown(text)
        self.result_label.setText(html)
        self.result_scroll.verticalScrollBar().setValue(0)
```

- [ ] **Step 2: 验证语法**

Run: `python3 -m py_compile app/widgets/script_panel.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/script_panel.py
git commit -m "feat(script): add SEO result handlers and _show_final_result"
```

---

### Task 5: 修改 _on_error 处理 SEO 失败回退

**Files:**
- Modify: `app/widgets/script_panel.py`（修改 `_on_error` 方法）

- [ ] **Step 1: 修改 _on_error 方法**

Read `_on_error` method (around line 598). Update it to handle SEO optimization failure:

```python
    def _on_error(self, msg: str):
        print(f"[剧本] === 生成失败 === {msg}")
        self._hide_progress()
        if hasattr(self, "_worker") and isinstance(self._worker, SEOOptimizeWorker):
            # SEO 阶段失败
            self.result_label.setText(
                f"<p style='color:#f85149'>❌ SEO 优化失败: {msg}</p>"
            )
        else:
            # 剧本生成阶段失败
            self.result_label.setText(
                f"<p style='color:#f85149'>❌ 生成失败: {msg}</p>"
            )
        self.gen_btn.setEnabled(True)
        self.modify_btn.setEnabled(True)
        self.gen_btn.setText("✨ AI 生成剧本")
```

- [ ] **Step 2: 验证语法**

Run: `python3 -m py_compile app/widgets/script_panel.py && echo "OK"`

- [ ] **Step 3: 提交**

```bash
git add app/widgets/script_panel.py
git commit -m "fix(script): handle errors for both generation and SEO phases"
```

---

## 自检清单

1. **Spec 覆盖**：两阶段流程 ✓、SEOOptimizeWorker ✓、_run_seo_optimize ✓、_on_seo_result ✓
2. **占位符扫描**：无 TBD/TODO ✓
3. **类型一致性**：所有方法签名一致 ✓

---

**Plan 完成！**
