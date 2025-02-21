import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from tkinterdnd2 import *  # 导入所有组件，包括 DND_FILES
import threading
import os
from src.node_parser import NodeParser
from src.translator import Translator
from src.file_utils import FileUtils
import sys
import json
import time
from src.translation_config import TranslationServices
from src.diff_tab import DiffTab
from typing import List
import logging  # 添加日志模块
import shutil

class ComfyUITranslator:
    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI 节点翻译 - 作者 OldX")
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(message)s'
        )
        
        # 设置最小窗口大小
        self.root.minsize(900, 800)
        
        # 获取屏幕尺寸
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # 设置窗口初始大小为屏幕的 80%
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # 设置窗口位置为屏幕中央
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 配置根窗口的网格权重，使内容可以跟随窗口调整
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架的网格权重
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # 加载配置
        self.config = self._load_config()
        
        # 创建标签页
        self.tab_control = ttk.Notebook(self.main_frame)
        self.tab_control.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 创建翻译功能标签页
        self.translation_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.translation_tab, text="翻译功能")
        
        # 创建对比功能标签页
        self.diff_tab = DiffTab(self.tab_control)
        self.tab_control.add(self.diff_tab, text="对比功能")
        
        # 创建操作说明标签页
        self.help_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.help_tab, text="操作说明")
        self.setup_help_ui()

        # 在翻译功能标签页中添加控件
        self.setup_translation_ui()
        
        # 初始化其他属性
        self.translating = False
        self.detected_nodes = {}
        self.json_window = None
        
        # 创建工作目录
        self.work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
        os.makedirs(self.work_dir, exist_ok=True)
        
        # 初始化变量
        self.folder_path = tk.StringVar()  # 添加 folder_path 变量
        self.plugin_folders = []  # 存储选择的文件夹列表
        
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.log(f"已选择文件夹: {folder}")
            
    def log(self, message):
        """添加日志"""
        logging.info(message)  # 在终端显示日志
        self.log_text.insert(tk.END, f"[{message}]\n")  # 在 GUI 中显示日志
        self.log_text.see(tk.END)
        
    def detect_nodes(self):
        """检测文件夹中的节点"""
        if hasattr(self, 'plugin_folders') and self.plugin_folders:
            # 批量处理模式
            self.detect_batch_nodes()
        else:
            # 单文件夹模式
            if not self.folder_path.get():
                tk.messagebox.showerror("错误", "请先选择插件文件夹！")
                return
            self.detect_single_folder()

    def detect_single_folder(self):
        """检测单个文件夹的节点"""
        self.detect_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.view_json_btn.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.detected_nodes = {}
        
        # 获取插件专属的输出目录
        plugin_dirs = FileUtils.get_plugin_output_dir(
            os.path.dirname(os.path.abspath(__file__)),
            self.folder_path.get()
        )
        
        # 在新线程中运行检测任务
        threading.Thread(
            target=self.detection_task,
            args=(plugin_dirs,),  # 只传递 plugin_dirs 参数
            daemon=True
        ).start()

    def detect_batch_nodes(self):
        """批量检测多个文件夹的节点"""
        self.detect_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.view_json_btn.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.detected_nodes = {}
        
        # 在新线程中运行批量检测任务
        threading.Thread(
            target=self.batch_detection_task,
            daemon=True
        ).start()

    def batch_detection_task(self):
        """批量检测任务"""
        try:
            total_plugins = len(self.plugin_folders)
            total_nodes = 0
            
            # 创建时间戳目录
            self.current_output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "output",
                time.strftime("%Y%m%d_%H%M%S")
            )
            # 创建待翻译文件目录
            nodes_dir = os.path.join(self.current_output_dir, "nodes_to_translate")
            os.makedirs(nodes_dir, exist_ok=True)
            os.makedirs(os.path.join(self.current_output_dir, "temp"), exist_ok=True)
            
            self.log(f"[初始化] 创建输出目录: {self.current_output_dir}")
            
            for i, plugin_folder in enumerate(self.plugin_folders, 1):
                plugin_name = os.path.basename(plugin_folder)
                self.log(f"\n[检测进度] 正在检测第 {i}/{total_plugins} 个插件: {plugin_name}")
                
                # 初始化解析器
                node_parser = NodeParser(plugin_folder)
                
                # 扫描并解析节点
                nodes = node_parser.parse_folder(plugin_folder)
                
                # 优化节点信息
                nodes = node_parser.optimize_node_info(nodes)
                
                # 保存检测结果到时间戳目录
                output_file = os.path.join(nodes_dir, f'{plugin_name}_nodes.json')
                FileUtils.save_json(nodes, output_file)
                
                # 更新总节点数
                total_nodes += len(nodes)
                
                # 更新进度
                progress = int((i / total_plugins) * 100)
                self.root.after(0, lambda: self.progress.configure(value=progress))
                
                # 将节点添加到总结果中
                self.detected_nodes.update(nodes)
                
                self.log(f"[检测完成] 在插件 {plugin_name} 中找到 {len(nodes)} 个待翻译节点")
            
            self.log(f"\n[检测完成] 共在 {len(self.plugin_folders)} 个插件中找到 {total_nodes} 个待翻译节点")
            
            # 启用按钮
            if total_nodes > 0:
                self.root.after(0, lambda: [
                    self.detect_btn.config(state=tk.NORMAL),
                    self.start_btn.config(state=tk.NORMAL),
                    self.view_json_btn.config(state=tk.NORMAL)
                ])
                
        except Exception as e:
            self.log(f"[错误] 批量检测失败: {str(e)}")
            logging.error(f"批量检测失败: {str(e)}")
            # 恢复按钮状态
            self.root.after(0, lambda: [
                self.detect_btn.config(state=tk.NORMAL),
                self.view_json_btn.config(state=tk.DISABLED)
            ])

    def detection_task(self, plugin_dirs: dict):
        """节点检测任务"""
        try:
            # 创建时间戳目录（如果不存在）
            if not hasattr(self, 'current_output_dir'):
                self.current_output_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "output",
                    time.strftime("%Y%m%d_%H%M%S")
                )
                os.makedirs(self.current_output_dir, exist_ok=True)
                
            # 创建待翻译文件目录
            nodes_dir = os.path.join(self.current_output_dir, "nodes_to_translate")
            os.makedirs(nodes_dir, exist_ok=True)
            
            # 初始化解析器
            node_parser = NodeParser(self.folder_path.get())
            
            # 扫描并解析节点
            self.detected_nodes = node_parser.parse_folder(self.folder_path.get())
            
            # 优化节点信息
            self.detected_nodes = node_parser.optimize_node_info(self.detected_nodes)
            
            # 保存检测结果到时间戳目录
            plugin_name = os.path.basename(self.folder_path.get())
            output_file = os.path.join(nodes_dir, f"{plugin_name}_nodes.json")
            FileUtils.save_json(self.detected_nodes, output_file)
            
            # 生成详细日志
            self._generate_detail_log(self.detected_nodes, plugin_dirs)
            
            # 获取文件数量（从源文件信息中）
            source_files = set()
            for node_info in self.detected_nodes.values():
                if '_source_file' in node_info:
                    source_files.add(node_info['_source_file'])
            
            total_nodes = len(self.detected_nodes)
            self.log(f"检测完成！共找到 {total_nodes} 个节点在 {len(source_files)} 个文件中")
            # 添加保存路径信息
            self.log(f"检测结果已保存至: {output_file}")
            
            # 启用开始翻译按钮
            if total_nodes > 0:
                self.root.after(0, lambda: [
                    self.detect_btn.config(state=tk.NORMAL),
                    self.start_btn.config(state=tk.NORMAL),
                    self.view_json_btn.config(state=tk.NORMAL)
                ])
                
        except Exception as e:
            self.log(f"[错误] 检测失败: {str(e)}")
            logging.error(f"检测失败: {str(e)}")
            # 恢复按钮状态
            self.root.after(0, lambda: [
                self.detect_btn.config(state=tk.NORMAL),
                self.view_json_btn.config(state=tk.DISABLED)
            ])

    def test_api(self):
        """测试 API 连接"""
        api_key = self.api_key.get().strip()
        model_id = self.model_id.get().strip()
        
        if not api_key:
            tk.messagebox.showerror("错误", "请输入 API 密钥！")
            return
        
        if not model_id:
            tk.messagebox.showerror("错误", "请输入模型 ID！")
            return
        
        self.test_api_btn.config(state=tk.DISABLED)
        self.test_api_btn.config(text="正在测试...")
        
        def test_task():
            try:
                translator = Translator(api_key, model_id)
                if translator.test_connection():
                    def on_success():
                        tk.messagebox.showinfo("成功", "API 连接测试成功！")
                        self.test_api_btn.config(state=tk.NORMAL, text="测试API")
                        # 保存配置
                        self._save_api_key(api_key)
                    self.root.after(0, on_success)
            except Exception as e:
                def on_error():
                    tk.messagebox.showerror("错误", str(e))
                    self.test_api_btn.config(state=tk.NORMAL, text="测试API")
                self.root.after(0, on_error)
        
        threading.Thread(target=test_task, daemon=True).start()

    def _save_api_key(self, api_key: str):
        """保存 API 密钥和模型 ID"""
        config = {
            "api_keys": {
                "volcengine": api_key
            },
            "model_ids": {
                "volcengine": self.model_id.get()  # 同时保存当前的模型 ID
            }
        }
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            tk.messagebox.showerror("错误", f"保存配置失败：{str(e)}")

    def view_results(self):
        """查看翻译结果"""
        try:
            if not hasattr(self, 'current_output_dir') or not self.current_output_dir:
                messagebox.showerror("错误", "没有可查看的翻译结果！")
                return
            
            if not os.path.exists(self.current_output_dir):
                messagebox.showerror("错误", "翻译结果目录不存在！")
                return
            
            # 打开文件夹
            if sys.platform == 'win32':  # Windows
                os.startfile(self.current_output_dir)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{self.current_output_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{self.current_output_dir}"')
            
        except Exception as e:
            error_msg = f"打开结果文件夹失败：{str(e)}"
            logging.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def _generate_detail_log(self, nodes: dict, plugin_dirs: dict):
        """生成详细日志"""
        try:
            # 清空详细日志
            self.detail_text.delete('1.0', tk.END)
            
            # 写入日志头
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.detail_text.insert(tk.END, f"ComfyUI 节点检测详细日志 ({timestamp})\n")
            self.detail_text.insert(tk.END, "=" * 50 + "\n\n")
            
            # 写入检测配置信息
            self.detail_text.insert(tk.END, "检测配置:\n")
            self.detail_text.insert(tk.END, f"- 插件目录: {self.folder_path.get()}\n")
            self.detail_text.insert(tk.END, f"- 检测时间: {timestamp}\n")
            
            # 写入统计信息
            source_files = set()
            total_inputs = 0
            total_outputs = 0
            total_widgets = 0
            for node_info in nodes.values():
                if '_source_file' in node_info:
                    source_files.add(node_info['_source_file'])
                total_inputs += len(node_info.get('inputs', {}))
                total_outputs += len(node_info.get('outputs', {}))
                total_widgets += len(node_info.get('widgets', {}))
            
            self.detail_text.insert(tk.END, "\n检测结果统计:\n")
            self.detail_text.insert(tk.END, f"- 扫描文件数: {len(source_files)}\n")
            self.detail_text.insert(tk.END, f"- 检测到节点数: {len(nodes)}\n")
            self.detail_text.insert(tk.END, f"- 待翻译字段总数: {total_inputs + total_outputs + total_widgets}\n")
            self.detail_text.insert(tk.END, f"  • 输入参数: {total_inputs}\n")
            self.detail_text.insert(tk.END, f"  • 输出参数: {total_outputs}\n")
            self.detail_text.insert(tk.END, f"  • 部件参数: {total_widgets}\n")
            
            # 写入检测结果保存路径
            output_file = os.path.join(plugin_dirs["temp"], 'nodes_to_translate.json')
            self.detail_text.insert(tk.END, f"\n检测结果保存路径: {output_file}\n")
            self.detail_text.insert(tk.END, "=" * 50 + "\n\n")
            
            # 写入文件列表
            self.detail_text.insert(tk.END, "扫描的文件列表:\n")
            for file_path in sorted(source_files):
                file_size = os.path.getsize(file_path)
                file_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_path)))
                self.detail_text.insert(tk.END, f"- {file_path}\n")
                self.detail_text.insert(tk.END, f"  • 大小: {file_size/1024:.1f} KB\n")
                self.detail_text.insert(tk.END, f"  • 修改时间: {file_time}\n")
            
            self.detail_text.insert(tk.END, "\n" + "=" * 50 + "\n\n")
            
            # 按文件分组显示节点
            nodes_by_file = {}
            for node_name, node_info in nodes.items():
                file_path = node_info.get('_source_file', 'unknown')
                if file_path not in nodes_by_file:
                    nodes_by_file[file_path] = []
                nodes_by_file[file_path].append((node_name, node_info))
            
            # 写入每个文件的节点信息
            for file_path, file_nodes in nodes_by_file.items():
                self.detail_text.insert(tk.END, f"\n文件: {file_path}\n")
                self.detail_text.insert(tk.END, f"节点数量: {len(file_nodes)}\n")
                self.detail_text.insert(tk.END, "-" * 50 + "\n")
                
                for node_name, node_info in file_nodes:
                    # 显示原始节点名称和处理后的名称
                    base_name = node_name.split('(')[0]
                    self.detail_text.insert(tk.END, f"\n节点: {node_name}\n")
                    if base_name != node_name:
                        self.detail_text.insert(tk.END, f"翻译用名称: {base_name}\n")
                    
                    # 写入标题
                    if 'title' in node_info:
                        self.detail_text.insert(tk.END, f"标题: {node_info['title']}\n")
                    
                    # 统计当前节点的参数数量
                    node_inputs = len(node_info.get('inputs', {}))
                    node_outputs = len(node_info.get('outputs', {}))
                    node_widgets = len(node_info.get('widgets', {}))
                    self.detail_text.insert(tk.END, f"\n参数统计: {node_inputs + node_outputs + node_widgets} 个\n")
                    
                    # 写入输入信息
                    if 'inputs' in node_info and node_info['inputs']:
                        self.detail_text.insert(tk.END, f"\n输入 ({node_inputs}):\n")
                        for input_name, input_info in node_info['inputs'].items():
                            self.detail_text.insert(tk.END, f"  - {input_name}: {input_info}\n")
                    
                    # 写入输出信息
                    if 'outputs' in node_info and node_info['outputs']:
                        self.detail_text.insert(tk.END, f"\n输出 ({node_outputs}):\n")
                        for output_name, output_info in node_info['outputs'].items():
                            self.detail_text.insert(tk.END, f"  - {output_name}: {output_info}\n")
                    
                    # 写入部件信息
                    if 'widgets' in node_info and node_info['widgets']:
                        self.detail_text.insert(tk.END, f"\n部件 ({node_widgets}):\n")
                        for widget_name, widget_info in node_info['widgets'].items():
                            self.detail_text.insert(tk.END, f"  - {widget_name}: {widget_info}\n")
                    
                    self.detail_text.insert(tk.END, "\n" + "-" * 30 + "\n")
            
            # 滚动到顶部
            self.detail_text.see('1.0')
            
        except Exception as e:
            self.log(f"生成详细日志失败: {str(e)}")

    def _update_translation_log(self, message: str):
        """更新翻译详细日志"""
        # 添加时间戳
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.detail_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.detail_text.see(tk.END)  # 滚动到底部

    def view_json(self):
        """查看待翻译的JSON文件"""
        try:
            if not hasattr(self, 'current_output_dir') or not self.current_output_dir:
                messagebox.showerror("错误", "请先执行节点检测！")
                return
            
            nodes_dir = os.path.join(self.current_output_dir, "nodes_to_translate")
            if not os.path.exists(nodes_dir):
                messagebox.showerror("错误", "未找到待翻译文件，请重新执行节点检测。")
                return
            
            if not os.listdir(nodes_dir):
                messagebox.showerror("错误", "未检测到任何待翻译节点，请重新检测。")
                return
            
            # 打开文件夹
            if sys.platform == 'win32':  # Windows
                os.startfile(nodes_dir)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{nodes_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{nodes_dir}"')
            
        except Exception as e:
            error_msg = f"打开待翻译文件夹失败：{str(e)}"
            logging.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def _load_config(self) -> dict:
        """从配置文件加载配置"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def setup_translation_ui(self):
        """设置翻译功能的用户界面"""
        # API密钥输入和服务商选择框架
        api_frame = ttk.Frame(self.translation_tab)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # API密钥输入
        ttk.Label(api_frame, text="API密钥:", width=8).pack(side=tk.LEFT)
        self.api_key = tk.StringVar(value=self.config.get("api_keys", {}).get("volcengine", ""))
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=60)
        self.api_key_entry.pack(side=tk.LEFT, padx=5)
        
        # 添加火山引擎 model ID 输入框
        ttk.Label(api_frame, text="模型ID:", width=8).pack(side=tk.LEFT, padx=(10, 0))
        self.model_id = tk.StringVar(value=self.config.get("model_ids", {}).get("volcengine", ""))
        self.model_id_entry = ttk.Entry(api_frame, textvariable=self.model_id, width=30)
        self.model_id_entry.pack(side=tk.LEFT, padx=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(api_frame)
        btn_frame.pack(side=tk.LEFT, padx=10)
        
        self.save_config_btn = ttk.Button(btn_frame, text="保存配置", width=10, command=self._save_api_key)
        self.save_config_btn.pack(side=tk.LEFT, padx=2)
        
        self.test_api_btn = ttk.Button(btn_frame, text="测试API", width=10, command=self.test_api)
        self.test_api_btn.pack(side=tk.LEFT, padx=2)
        
        # 修改文件夹选择框架
        folder_frame = ttk.LabelFrame(self.translation_tab, text="插件文件夹选择", padding=5)
        folder_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 修改拖放提示文本
        drop_label = ttk.Label(
            folder_frame, 
            text="请拖入插件文件夹",
            foreground='gray',
            font=('TkDefaultFont', 12)  # 增大标签字体
        )
        drop_label.pack(fill=tk.X, padx=5, pady=5)
        
        # 增大拖放区域高度和字体
        self.drop_area = tk.Text(
            folder_frame, 
            height=6, 
            width=50,
            font=('TkDefaultFont', 11)  # 增大文本区域字体
        )
        self.drop_area.pack(fill=tk.X, padx=5, pady=5)
        
        # 修改提示文本
        drop_text = (
            "第一步：打开comfyui\\custom_nodes文件夹\n"
            "第二步：选择需要翻译的插件文件夹，拖入该区域\n"
            "·可以多选后一次性拖入"
        )
        self.drop_area.insert('1.0', drop_text)
        self.drop_area.config(state='disabled')
        
        # 注册拖放目标和绑定事件
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.on_drop)
        
        # 按钮框架 - 只保留清除按钮
        btn_frame = ttk.Frame(folder_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.clear_folders_btn = ttk.Button(
            btn_frame,
            text="清除选择",
            width=15,
            command=self.clear_selected_folders,
            state=tk.DISABLED
        )
        self.clear_folders_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加插件列表显示
        plugins_frame = ttk.LabelFrame(self.translation_tab, text="待处理插件列表", padding=5)
        plugins_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.plugins_text = scrolledtext.ScrolledText(plugins_frame, height=5, width=80)
        self.plugins_text.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress = ttk.Progressbar(self.translation_tab, length=300, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=10)
        
        # 创建控制区域框架（包含按钮和翻译设置）
        control_frame = ttk.Frame(self.translation_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 左侧：控制按钮
        btn_frame = ttk.LabelFrame(control_frame, text="操作按钮", padding=5)
        btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        button_width = 15
        self.detect_btn = ttk.Button(btn_frame, text="检测节点", width=button_width, command=self.detect_nodes)
        self.detect_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_json_btn = ttk.Button(
            btn_frame, 
            text="查看待翻译JSON",
            width=button_width,
            command=self.view_json,
            state=tk.DISABLED
        )
        self.view_json_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(btn_frame, text="开始翻译", width=button_width, command=self.start_translation, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="终止翻译", width=button_width, command=self.stop_translation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_btn = ttk.Button(btn_frame, text="查看结果", width=button_width, command=self.view_results, state=tk.DISABLED)
        self.view_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧：翻译设置
        batch_frame = ttk.LabelFrame(control_frame, text="翻译设置", padding=5)
        batch_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        ttk.Label(batch_frame, text="一次性翻译节点数:").pack(side=tk.LEFT, padx=5)
        self.batch_size = tk.StringVar(value="6")
        batch_entry = ttk.Entry(batch_frame, textvariable=self.batch_size, width=5)
        batch_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(
            batch_frame, 
            text="(建议: 5-8, 数值越大速度越快，但可能超过模型上下文限制)"
        ).pack(side=tk.LEFT, padx=5)
        
        # 创建日志框架（左右布局）
        log_frame = ttk.Frame(self.translation_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 配置日志框架的网格
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_columnconfigure(1, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧：翻译日志
        left_frame = ttk.LabelFrame(log_frame, text="翻译日志", padding=5)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(left_frame, height=20, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：详细日志（隐藏标题）
        right_frame = ttk.LabelFrame(log_frame, text="", padding=5)  # 移除标题
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        self.detail_text = scrolledtext.ScrolledText(right_frame, height=20, width=60)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.pack_forget()  # 隐藏详细日志区域

    def select_batch_folder(self):
        """选择多个插件文件夹"""
        try:
            # 使用 askopenfilenames 并设置为只能选择文件夹
            folders = filedialog.askopenfilenames(
                title="选择插件文件夹中的任意文件（可多选）",
                initialdir=os.path.dirname(self.folder_path.get()) if self.folder_path.get() else None
            )
            
            if folders:
                # 获取选择的文件夹路径列表（去重）
                folder_paths = []
                for file_path in folders:
                    folder_path = os.path.dirname(file_path)
                    if folder_path not in folder_paths:
                        folder_paths.append(folder_path)
                
                # 初始化文件夹列表（如果不存在）
                if not hasattr(self, 'plugin_folders'):
                    self.plugin_folders = []
                
                # 添加新选择的文件夹（去重）
                for folder in folder_paths:
                    if folder not in self.plugin_folders:
                        self.plugin_folders.append(folder)
                
                # 显示插件列表
                self.display_plugin_list()
                
                # 在文件夹输入框中显示选择的数量
                self.folder_path.set(f"已选择 {len(self.plugin_folders)} 个插件文件夹")
                
                # 启用检测按钮
                self.detect_btn.config(state=tk.NORMAL)
                
                # 启用清除按钮
                self.clear_folders_btn.config(state=tk.NORMAL)
                
        except Exception as e:
            messagebox.showerror("错误", f"选择文件夹失败: {str(e)}")

    def display_plugin_list(self):
        """显示待处理的插件列表"""
        self.plugins_text.delete('1.0', tk.END)
        if hasattr(self, 'plugin_folders') and self.plugin_folders:
            self.plugins_text.insert(tk.END, "待处理插件列表:\n\n")
            for i, folder in enumerate(self.plugin_folders, 1):
                folder_name = os.path.basename(folder)
                folder_path = folder
                self.plugins_text.insert(tk.END, f"{i}. {folder_name}\n   路径: {folder_path}\n\n")
        else:
            self.plugins_text.insert(tk.END, "未选择任何插件文件夹")

    def start_translation(self):
        """开始翻译"""
        if hasattr(self, 'plugin_folders') and self.plugin_folders:
            # 批量处理模式
            self.batch_translation()
        else:
            # 单文件处理模式(原有逻辑)
            self.single_translation()
        
    def stop_translation(self):
        """停止翻译任务"""
        self.translating = False
        self.detect_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # 不在这里修改查看结果按钮的状态
        self.log("翻译已终止")
        
    def batch_translation(self):
        """批量处理多个插件"""
        # 验证 API 密钥和模型 ID
        api_key = self.api_key.get().strip()
        model_id = self.model_id.get().strip()
        
        if not api_key or not model_id:
            tk.messagebox.showerror("错误", "请输入 API 密钥和模型 ID！")
            return
        
        # 验证批次大小
        try:
            batch_size = int(self.batch_size.get())
            if batch_size < 1:
                raise ValueError("批次大小必须大于 0")
        except ValueError as e:
            tk.messagebox.showerror("错误", f"批次大小设置无效: {str(e)}")
            return
        
        # 禁用按钮
        self.start_btn.config(state=tk.DISABLED)
        self.detect_btn.config(state=tk.DISABLED)
        self.clear_folders_btn.config(state=tk.DISABLED)  # 只禁用清除按钮
        
        # 在新线程中运行批量处理任务
        threading.Thread(
            target=self.batch_translation_task,
            args=(api_key, batch_size, model_id),
            daemon=True
        ).start()

    def batch_translation_task(self, api_key: str, batch_size: int, model_id: str):
        """批量翻译任务"""
        try:
            # 1. 创建时间戳目录
            self.current_output_dir = os.path.join(  # 保存当前输出目录路径
                os.path.dirname(os.path.abspath(__file__)),
                "output",
                time.strftime("%Y%m%d_%H%M%S")
            )
            os.makedirs(self.current_output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.current_output_dir, "temp"), exist_ok=True)
            
            self.log(f"[初始化] 创建翻译输出目录: {self.current_output_dir}")
            
            # 2. 开始翻译
            total_plugins = len(self.plugin_folders)
            self.translating = True
            self.stop_btn.config(state=tk.NORMAL)
            
            successful_translations = []  # 记录成功的翻译
            
            for i, plugin_folder in enumerate(self.plugin_folders, 1):
                if not self.translating:
                    raise Exception("翻译已被用户终止")
                
                plugin_name = os.path.basename(plugin_folder)
                self.log(f"\n[翻译进度] 正在翻译第 {i}/{total_plugins} 个插件: {plugin_name}")
                
                try:
                    # 2.1 翻译节点
                    translated_nodes = self._translate_single_plugin(
                        plugin_folder,
                        plugin_name,
                        api_key,
                        model_id,
                        batch_size,
                        self.current_output_dir
                    )
                    
                    # 2.2 保存翻译结果
                    result_file = os.path.join(self.current_output_dir, f"{plugin_name}.json")
                    FileUtils.save_json(translated_nodes, result_file)
                    
                    # 2.3 验证保存结果
                    if not os.path.exists(result_file):
                        raise Exception(f"保存失败: {result_file}")
                    
                    successful_translations.append({
                        'plugin_name': plugin_name,
                        'result_file': result_file
                    })
                    
                    self.log(f"[完成] 插件 {plugin_name} 翻译完成")
                    
                except Exception as e:
                    self.log(f"[错误] 插件 {plugin_name} 翻译失败: {str(e)}")
                    continue
            
            # 3. 清理临时文件
            temp_dir = os.path.join(self.current_output_dir, "temp")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            # 4. 完成处理
            if successful_translations:
                self.log(f"\n[完成] 翻译任务结束，成功翻译 {len(successful_translations)} 个插件")
                self.log(f"[输出] 翻译结果已保存到: {self.current_output_dir}")
                
                # 清理临时文件和待翻译文件
                nodes_dir = os.path.join(self.current_output_dir, "nodes_to_translate")
                temp_dir = os.path.join(self.current_output_dir, "temp")
                
                for dir_to_clean in [nodes_dir, temp_dir]:
                    if os.path.exists(dir_to_clean):
                        try:
                            shutil.rmtree(dir_to_clean)
                            self.log(f"[清理] 已清理临时文件: {os.path.basename(dir_to_clean)}")
                        except Exception as e:
                            self.log(f"[警告] 清理临时文件失败: {str(e)}")
                
                # 启用查看结果按钮
                self.root.after(0, lambda: self.view_btn.config(state=tk.NORMAL))
            else:
                self.log("\n[警告] 所有插件翻译均失败")
                
        except Exception as e:
            if str(e) != "翻译已被用户终止":
                self.log(f"[错误] 批量处理出错: {str(e)}")
                logging.error(f"批量处理出错: {str(e)}")
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: [
                self.start_btn.config(state=tk.NORMAL),
                self.detect_btn.config(state=tk.NORMAL),
                self.clear_folders_btn.config(state=tk.NORMAL)
            ])
            self.stop_translation()

    def clear_selected_folders(self):
        """清除已选择的文件夹列表"""
        if hasattr(self, 'plugin_folders'):
            self.plugin_folders = []
            self.folder_path.set("")
            self.display_plugin_list()
            self.clear_folders_btn.config(state=tk.DISABLED)

    def on_drop(self, event):
        """处理文件夹拖放事件"""
        try:
            # 获取拖放的路径
            data = event.data
            paths = data.split()  # Windows 下路径以空格分隔
            
            # 初始化文件夹列表（如果不存在）
            if not hasattr(self, 'plugin_folders'):
                self.plugin_folders = []
            
            # 处理每个路径
            for path in paths:
                # 移除可能的引号和空格
                path = path.strip('" ')
                
                if os.path.isdir(path):
                    # 如果是文件夹且不在列表中，添加它
                    if path not in self.plugin_folders:
                        self.plugin_folders.append(path)
                        logging.info(f"添加文件夹: {path}")
                elif os.path.isfile(path):
                    # 如果是文件，获取其所在文件夹
                    folder_path = os.path.dirname(path)
                    if folder_path not in self.plugin_folders:
                        self.plugin_folders.append(folder_path)
                        logging.info(f"添加文件夹: {folder_path}")
            
            # 更新显示
            self.display_plugin_list()
            
            # 更新文件夹输入框
            self.folder_path.set(f"已选择 {len(self.plugin_folders)} 个插件文件夹")
            
            # 启用相关按钮
            self.detect_btn.config(state=tk.NORMAL)
            self.clear_folders_btn.config(state=tk.NORMAL)
            
            # 更新拖放区域文本
            self.drop_area.configure(state='normal')
            self.drop_area.delete('1.0', tk.END)
            self.drop_area.insert('1.0',
                "第一步：打开comfyui\\custom_nodes文件夹\n"
                "第二步：选择需要翻译的插件文件夹，拖入该区域\n"
                "·可以多选后一次性拖入"
            )
            self.drop_area.configure(state='disabled')
            
        except Exception as e:
            error_msg = f"处理拖放文件夹失败: {str(e)}"
            logging.error(error_msg)  # 在终端显示错误
            messagebox.showerror("错误", error_msg)  # 同时显示错误对话框

    def _translate_single_plugin(self, plugin_folder: str, plugin_name: str,
                               api_key: str, model_id: str, batch_size: int,
                               timestamp_dir: str) -> dict:
        """翻译单个插件"""
        # 1. 解析节点
        node_parser = NodeParser(plugin_folder)
        nodes = node_parser.parse_folder(plugin_folder)
        
        if not nodes:
            raise Exception("未检测到节点")
        
        # 2. 优化节点信息
        nodes = node_parser.optimize_node_info(nodes)
        
        # 3. 翻译节点
        translator = Translator(api_key=api_key, model_id=model_id)
        
        def update_progress(progress: int, message: str = None):
            if not self.translating:
                raise Exception("翻译已被用户终止")
            if message:
                # 修改进度消息格式
                if "[翻译]" in message:
                    message = message.replace("[翻译]", "[翻译进度] 正在翻译")
                elif "[验证]" in message:
                    message = message.replace("[验证]", "[验证] 正在校验")
                self.log(message)
        
        # 创建临时目录
        temp_dir = os.path.join(timestamp_dir, "temp", plugin_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        translated_nodes = translator.translate_nodes(
            nodes,
            folder_path=plugin_folder,
            batch_size=batch_size,
            update_progress=update_progress,
            temp_dir=temp_dir  # 为每个插件创建独立的临时目录
        )
        
        return translated_nodes

    def setup_help_ui(self):
        """设置操作说明界面"""
        # 创建滚动文本框
        help_text = scrolledtext.ScrolledText(
            self.help_tab,
            wrap=tk.WORD,
            width=80,
            height=30,
            font=('TkDefaultFont', 10)
        )
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 添加操作说明内容
        help_content = """
# 操作说明

## 使用步骤

### 第一步：打开插件文件夹
- 打开 `comfyui\\custom_nodes` 文件夹，确保其中包含您要翻译的插件文件夹。

### 第二步：拖入插件文件夹
- 选择需要翻译的插件文件夹，拖入程序的拖放区域。
- 支持多选后一次性拖入。

### 第三步：配置 API
- 在程序中输入火山引擎的 API 密钥和模型 ID。
- 点击"测试 API"按钮，确保连接正常。

### 第四步：检测节点
- 点击"检测节点"按钮，程序将扫描插件中的节点信息。
- 检测完成后，您可以点击"查看待翻译 JSON"按钮，查看检测到的节点。

### 第五步：开始翻译
- 设置一次性翻译的节点数（建议：5-8）。
- 点击"开始翻译"按钮，程序将开始翻译过程。

### 第六步：查看翻译结果
- 翻译完成后，您可以点击"查看结果"按钮，打开当前翻译的结果时间戳文件夹。

## 注意事项
- 确保有稳定的网络连接。
- API 密钥请妥善保管，不要泄露。
- 建议先用小批量测试翻译效果。
- 如遇到问题，查看日志获取详细信息。

## 相关链接
- [火山引擎 API 配置说明](https://www.bilibili.com/video/BV1LCN2eZEAX/?spm_id_from=333.1387.homepage.video_card.click&vd_source=ae85ec1de21e4084d40c5d4eec667b8f)
- [程序配套的视频讲解](https://www.bilibili.com/video/BV1hmAneGEbZ/?share_source=copy_web&vd_source=af996d4f530575a9634db534351104a6)
"""
        
        help_text.insert('1.0', help_content)
        help_text.config(state='disabled')  # 设置为只读

def setup_styles():
    """设置自定义样式"""
    style = ttk.Style()
    
    # 配置开关按钮样式
    style.configure(
        'Switch.TCheckbutton',
        background='white',
        foreground='black',
        padding=5
    )
    
    # 如果系统支持，可以使用更现代的开关样式
    try:
        style.element_create('Switch.slider', 'from', 'clam')
        style.layout('Switch.TCheckbutton',
            [('Checkbutton.padding',
                {'children': [
                    ('Switch.slider', {'side': 'left', 'sticky': ''}),
                    ('Checkbutton.label', {'side': 'right', 'sticky': ''})
                ]})
            ])
    except tk.TclError:
        pass  # 如果不支持，就使用默认复选框样式

def main():
    root = TkinterDnD.Tk()  # 使用 TkinterDnD 的 Tk
    setup_styles()  # 设置样式
    app = ComfyUITranslator(root)
    root.mainloop()

if __name__ == "__main__":
    main() 