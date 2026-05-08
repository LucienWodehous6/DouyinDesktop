"""PipelineWorker — 串行执行多 Agent 流水线的后台线程"""

import os
from PyQt6.QtCore import QThread, pyqtSignal


class PipelineWorker(QThread):
    """串行执行多 Agent 流水线的后台线程"""

    log_signal = pyqtSignal(str, str)  # (agent_name, message)
    progress_signal = pyqtSignal(int, str)  # (percent, status)
    agent_done_signal = pyqtSignal(str, str)  # (agent_name, result_file)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, agents: list[dict], output_dir: str):
        super().__init__()
        self.agents = agents  # [{"Name": "CDO", "config": {...}}, ...]
        self.output_dir = output_dir
        self._stop = False
        os.makedirs(output_dir, exist_ok=True)

    def stop(self):
        self._stop = True

    def run(self):
        try:
            total = len(self.agents)
            for i, agent in enumerate(self.agents):
                if self._stop:
                    break
                percent = int((i / total) * 100)
                self.progress_signal.emit(percent, f"执行中: {agent['Name']}")
                self._run_agent(agent)

            if not self._stop:
                self._cleanup_output_files()
                self.progress_signal.emit(100, "完成")
                self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_agent(self, agent: dict):
        """执行单个 Agent"""
        name = agent["Name"]
        config = agent["config"]
        self.log_signal.emit(name, f"开始执行 {name}...")

        if name == "CDO":
            result = self._run_cdo(config)
        elif name == "CCO":
            result = self._run_cco(config)
        elif name == "SEO":
            result = self._run_seo(config)
        elif name == "CMO":
            result = self._run_cmo(config)
        else:
            raise ValueError(f"Unknown agent: {name}")

        self.agent_done_signal.emit(name, result)
        self.log_signal.emit(name, f"{name} 执行完成")

    def _run_cdo(self, config: dict) -> str:
        from app.widgets.workflow.agents.cdo_agent import CDOAgentWorker
        result_file = os.path.join(self.output_dir, "cdoresult.json")
        worker = CDOAgentWorker(
            keyword=config.get("keyword", ""),
            platform=config.get("platform", "抖音"),
            count=config.get("count", 20),
            output_file=result_file,
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_cco(self, config: dict) -> str:
        from app.widgets.workflow.agents.cco_agent import CCOAgentWorker
        input_file = os.path.join(self.output_dir, "cdoresult.json")
        result_file = os.path.join(self.output_dir, "ccoresult.md")
        worker = CCOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
            style=config.get("style", "neutral"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_seo(self, config: dict) -> str:
        from app.widgets.workflow.agents.seo_agent import SEOAgentWorker
        input_file = os.path.join(self.output_dir, "ccoresult.md")
        result_file = os.path.join(self.output_dir, "seoresult.md")
        worker = SEOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _run_cmo(self, config: dict) -> str:
        from app.widgets.workflow.agents.cmo_agent import CMOAgentWorker
        input_file = os.path.join(self.output_dir, "seoresult.md")
        result_file = os.path.join(self.output_dir, "cmoresult.json")
        worker = CMOAgentWorker(
            input_file=input_file,
            output_file=result_file,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com/v1"),
            model=config.get("model", "deepseek-chat"),
            target_platform=config.get("target_platform", "抖音"),
        )
        worker.finished_signal.connect(lambda: worker.deleteLater())
        worker.start()
        worker.wait()
        return result_file

    def _cleanup_output_files(self):
        """流程完成后自动清理所有输出文件"""
        files = ["cdoresult.json", "ccoresult.md", "seoresult.md", "cmoresult.json"]
        for f in files:
            path = os.path.join(self.output_dir, f)
            if os.path.exists(path):
                os.remove(path)
                self.log_signal.emit("Pipeline", f"已清理: {f}")