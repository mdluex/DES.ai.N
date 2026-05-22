import sys
import os
import time
import base64
from threading import Thread
from PyQt5 import QtCore, QtWidgets
from ui.main_window import DesignApp
from core.photoshop_client import PhotoshopClient
from core.ai_agent import DesignAgent

class BackendWorker(QtCore.QObject):
    system_message = QtCore.pyqtSignal(str)
    agent_message = QtCore.pyqtSignal(str)
    tool_message = QtCore.pyqtSignal(str)
    preview_ready = QtCore.pyqtSignal(str)
    task_started = QtCore.pyqtSignal()    # emitted when agent loop begins
    task_finished = QtCore.pyqtSignal()   # emitted when agent loop ends

    def __init__(self, output_folder, templates_folder):
        super().__init__()
        self.output_folder = output_folder
        self.templates_folder = templates_folder
        self.ps_client = PhotoshopClient(self.emit_log)
        self.agent = None
        self._stop = False   # set True to interrupt the running task

    def request_stop(self):
        """Signal the running task to stop after the current tool call."""
        self._stop = True
        self.emit_log("[SYSTEM] Stop requested — finishing current step then halting...")

    def emit_log(self, msg):
        if msg.startswith("[AGENT]"):
            self.agent_message.emit(msg[8:].strip())
        elif msg.startswith("[AGENT: TOOL CALL]"):
            self.tool_message.emit(msg[19:].strip())
        elif msg.startswith("[VISION: TOOL CALL]"):
            self.tool_message.emit(f"Vision Tool: {msg[20:].strip()}")
        else:
            self.system_message.emit(msg.replace("[SYSTEM] ", "").replace("[INFO] ", "").replace("[ERROR] ", "Error: "))

    def process_chat(self, msg, api_url, api_key, save_psd, templates_folder, output_folder):
        self.templates_folder = templates_folder
        self.output_folder = output_folder
        
        if not self.agent:
            self.ps_client.connect()
            self.agent = DesignAgent(api_url, api_key, self.ps_client, self.output_folder, self.templates_folder, self.emit_log, self.preview_ready.emit)
            available_templates = os.listdir(self.templates_folder) if os.path.exists(self.templates_folder) else []
            self.agent.init_session(msg, available_templates, save_psd)
        else:
            self.agent.api_url = api_url
            self.agent.api_key = api_key
            self.agent.templates_folder = self.templates_folder
            self.agent.output_folder = self.output_folder
            self.agent.add_user_chat(msg, save_psd)
            
        self.run_agent_cycle()

    def process_reference(self, ref_path, user_note, api_url, api_key, save_psd, templates_folder, output_folder):
        self.templates_folder = templates_folder
        self.output_folder = output_folder

        if not self.agent:
            self.ps_client.connect()
            self.agent = DesignAgent(api_url, api_key, self.ps_client, self.output_folder, self.templates_folder, self.emit_log, self.preview_ready.emit)
        else:
            self.agent.api_url = api_url
            self.agent.api_key = api_key
            self.agent.templates_folder = self.templates_folder
            self.agent.output_folder = self.output_folder

        available_templates = os.listdir(self.templates_folder) if os.path.exists(self.templates_folder) else []
        self.agent.init_reference_session(ref_path, user_note, available_templates, save_psd)
        self.run_agent_cycle()

    def run_agent_cycle(self):
        self._stop = False
        self.task_started.emit()
        try:
            success = self.agent.run_agent_loop(stop_flag=lambda: self._stop)
        finally:
            self._stop = False
            self.task_finished.emit()
            self.emit_log("[SYSTEM] Agent cycle complete. Awaiting next command...")

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    psd_folder = os.path.join(current_dir, "templates")
    output_folder = os.path.join(current_dir, "output")
    os.makedirs(psd_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    
    window = DesignApp(psd_folder, output_folder)
    worker = BackendWorker(output_folder, psd_folder)
    
    # Connect signals
    worker.system_message.connect(window.append_system_msg)
    worker.agent_message.connect(window.append_agent_msg)
    worker.tool_message.connect(window.append_tool_call)
    worker.preview_ready.connect(window.update_preview_image)
    worker.task_started.connect(lambda: window.set_task_running(True))
    worker.task_finished.connect(lambda: window.set_task_running(False))
    window.stop_requested.connect(worker.request_stop)
    
    def on_chat(msg, api_url, api_key, save_psd, templates_folder, output_folder):
        thread = Thread(target=worker.process_chat, args=(msg, api_url, api_key, save_psd, templates_folder, output_folder))
        thread.start()

    def on_reference(ref_path, user_note, api_url, api_key, save_psd, templates_folder, output_folder):
        thread = Thread(target=worker.process_reference, args=(ref_path, user_note, api_url, api_key, save_psd, templates_folder, output_folder))
        thread.start()

    window.chat_requested.connect(on_chat)
    window.reference_requested.connect(on_reference)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
