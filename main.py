import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
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

class ComfyUITranslator:
    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI 节点翻译 - 作者 OldX")
        
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

        # 在翻译功能标签页中添加控件
        self.setup_translation_ui()
        
        # 初始化其他属性
        self.translating = False
        self.detected_nodes = {}
        self.json_window = None
        
        # 创建工作目录
        self.work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
        os.makedirs(self.work_dir, exist_ok=True)
        
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.log(f"已选择文件夹: {folder}")
            
    def log(self, message):
        self.log_text.insert(tk.END, f"[{message}]\n")
        self.log_text.see(tk.END)
        
    def detect_nodes(self):
        """检测文件夹中的节点"""
        if not self.folder_path.get():
            tk.messagebox.showerror("错误", "请先选择插件文件夹！")
            return
            
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
            args=(plugin_dirs,),
            daemon=True
        ).start()
        
    def detection_task(self, plugin_dirs: dict):
        """节点检测任务"""
        try:
            # 初始化解析器
            node_parser = NodeParser(self.folder_path.get())
            
            # 扫描并解析节点
            self.detected_nodes = node_parser.parse_folder(self.folder_path.get())
            
            # 优化节点信息
            self.detected_nodes = node_parser.optimize_node_info(self.detected_nodes)
            
            # 保存检测结果到输出目录
            output_file = os.path.join(plugin_dirs["temp"], 'nodes_to_translate.json')
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
                    self.view_json_btn.config(state=tk.NORMAL)  # 检测完成后启用查看按钮
                ])
                
        except Exception as e:
            # 出错时恢复按钮状态
            self.root.after(0, lambda: [
                self.detect_btn.config(state=tk.NORMAL),
                self.view_json_btn.config(state=tk.DISABLED)  # 保持禁用状态
            ])
            self.log(f"检测失败: {str(e)}")
            
    def start_translation(self):
        """开始翻译"""
        if not self.detected_nodes:
            tk.messagebox.showerror("错误", "请先检测节点！")
            return
            
        # 验证批次大小
        try:
            batch_size = int(self.batch_size.get())
            if batch_size < 1:
                raise ValueError("批次大小必须大于 0")
        except ValueError as e:
            tk.messagebox.showerror("错误", f"批次大小设置无效: {str(e)}")
            return
            
        # 验证 API 密钥
        api_key = self.api_key.get().strip()
        if not api_key:
            tk.messagebox.showerror("错误", "请输入 API 密钥！")
            return
            
        # 验证火山引擎 model_id
        model_id = self.model_id.get().strip()
        if not model_id:
            tk.messagebox.showerror("错误", "请输入模型 ID！")
            return
        
        # 禁用按钮
        self.start_btn.config(state=tk.DISABLED)
        self.detect_btn.config(state=tk.DISABLED)
        
        # 开始翻译
        self.log(f"\n开始翻译 {len(self.detected_nodes)} 个节点...")
        self.log(f"使用模型: {model_id}")
        self.log(f"每批节点数: {batch_size}")
        
        # 在新线程中运行翻译任务
        threading.Thread(
            target=self.translation_task,
            args=(api_key, batch_size, model_id),
            daemon=True
        ).start()
        
    def stop_translation(self):
        self.translating = False
        self.detect_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # 如果存在翻译结果文件，则启用查看结果按钮
        complete_output = os.path.join(self.folder_path.get(), 'all_translations.json')
        if os.path.exists(complete_output):
            self.view_btn.config(state=tk.NORMAL)
        self.log("翻译已终止")
        
    def translation_task(self, api_key: str, batch_size: int, model_id: str):
        """翻译任务"""
        try:
            # 初始化翻译器
            translator = Translator(
                api_key=api_key,
                model_id=model_id
            )
            
            # 设置翻译状态
            self.translating = True
            self.stop_btn.config(state=tk.NORMAL)
            
            def update_progress(progress: int, message: str = None):
                if not self.translating:
                    raise Exception("翻译已被用户终止")
                self.root.after(0, lambda: self.progress.configure(value=progress))
                if message:
                    self.log(message)
            
            # 传递插件文件夹路径
            translated_nodes = translator.translate_nodes(
                self.detected_nodes,
                folder_path=self.folder_path.get(),
                batch_size=batch_size,
                update_progress=update_progress
            )
            
            # 添加调试日志
            self.log(f"获取到翻译结果: {len(translated_nodes)} 个节点")
            
            # 获取插件专属的输出目录
            plugin_dirs = FileUtils.get_plugin_output_dir(
                os.path.dirname(os.path.abspath(__file__)),
                self.folder_path.get()
            )
            
            # 保存完整的翻译结果
            plugin_name = os.path.basename(self.folder_path.get())
            final_file = os.path.join(plugin_dirs["translations"], f"{plugin_name}.json")
            
            try:
                FileUtils.save_json(translated_nodes, final_file)
                self.log(f"已保存翻译结果到: {final_file}")
                
                # 启用查看结果按钮
                self.root.after(0, lambda: self.view_btn.config(state=tk.NORMAL))
                
            except Exception as e:
                self.log(f"保存翻译结果失败: {str(e)}")
            
            if self.translating:
                self.log("翻译完成！")
                
            # 添加分隔线
            self.log("\n" + "=" * 30)
            self.log("翻译任务完成统计")
            self.log("-" * 20)
            
            # 显示统计信息
            self.log(f"处理节点数: {len(self.detected_nodes)}")
            self.log(f"批次大小: {batch_size}")
            self.log(f"总批次数: {(len(self.detected_nodes) + batch_size - 1) // batch_size}")
            
            # tokens 使用统计会通过 update_progress 回调显示
            
            self.log("=" * 30 + "\n")
            
        except Exception as e:
            self.log(f"翻译过程出错: {str(e)}")
            
        finally:
            self.stop_translation()

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
            if not self.folder_path.get():
                messagebox.showerror("错误", "请先选择插件文件夹！")
                return
            
            # 获取插件专属的输出目录
            plugin_dirs = FileUtils.get_plugin_output_dir(
                os.path.dirname(os.path.abspath(__file__)),
                self.folder_path.get()
            )
            
            # 获取翻译结果文件路径
            plugin_name = os.path.basename(self.folder_path.get())
            result_file = os.path.join(plugin_dirs["translations"], f"{plugin_name}.json")
            
            if not os.path.exists(result_file):
                messagebox.showerror("错误", "未找到翻译结果文件！")
                return
            
            # 使用系统默认程序打开 JSON 文件
            if sys.platform == 'win32':  # Windows
                os.startfile(result_file)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{result_file}"')
            else:  # Linux
                os.system(f'xdg-open "{result_file}"')
            
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败：{str(e)}")

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
        """打开待翻译的 JSON 文件"""
        try:
            if not self.folder_path.get():
                messagebox.showerror("错误", "请先选择插件文件夹！")
                return
            
            # 获取插件专属的输出目录
            plugin_dirs = FileUtils.get_plugin_output_dir(
                os.path.dirname(os.path.abspath(__file__)),
                self.folder_path.get()
            )
            
            # 获取最新的待翻译文件路径
            json_file = os.path.join(plugin_dirs["temp"], "nodes_to_translate.json")
            
            if not os.path.exists(json_file):
                messagebox.showerror("错误", "未找到待翻译的节点文件，请先检测节点！")
                return
            
            # 使用系统默认程序打开 JSON 文件
            if sys.platform == 'win32':  # Windows
                os.startfile(json_file)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{json_file}"')
            else:  # Linux
                os.system(f'xdg-open "{json_file}"')
            
        except Exception as e:
            messagebox.showerror("错误", f"打开 JSON 文件失败: {str(e)}")

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
        
        # 文件夹选择框架
        folder_frame = ttk.Frame(self.translation_tab)
        folder_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(folder_frame, text="插件文件夹:", width=10).pack(side=tk.LEFT)
        self.folder_path = tk.StringVar()
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path)
        self.folder_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.folder_btn = ttk.Button(folder_frame, text="选择文件夹", width=12, command=self.select_folder)
        self.folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(self.translation_tab, length=300, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=10)
        
        # 控制按钮框架
        btn_frame = ttk.Frame(self.translation_tab)
        btn_frame.pack(pady=5)
        
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
        
        # 创建日志区域
        log_frame = ttk.LabelFrame(self.translation_tab, text="翻译日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建详细日志文本框
        detail_frame = ttk.LabelFrame(self.translation_tab, text="详细日志", padding=5)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=20, width=80)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 翻译设置框架
        batch_frame = ttk.LabelFrame(self.translation_tab, text="翻译设置", padding=5)
        batch_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(batch_frame, text="一次性翻译节点数:").pack(side=tk.LEFT, padx=5)
        self.batch_size = tk.StringVar(value="6")
        batch_entry = ttk.Entry(batch_frame, textvariable=self.batch_size, width=5)
        batch_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(
            batch_frame, 
            text="(建议: 5-8, 数值越大速度越快，但可能超过模型上下文限制)"
        ).pack(side=tk.LEFT, padx=5)

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
    root = tk.Tk()
    setup_styles()  # 设置样式
    app = ComfyUITranslator(root)
    root.mainloop()

if __name__ == "__main__":
    main() 