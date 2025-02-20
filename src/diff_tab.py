import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
from .node_diff import NodeDiffer

class DiffTab(ttk.Frame):
    """节点对比标签页"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        self.output_file = None  # 保存输出文件路径
        
    def setup_ui(self):
        """设置用户界面"""
        # 旧文件选择框
        old_frame = ttk.LabelFrame(self, text="旧版本节点文件", padding=5)
        old_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.old_path = tk.StringVar()
        ttk.Entry(old_frame, textvariable=self.old_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(old_frame, text="选择文件", command=self.select_old_file).pack(side=tk.LEFT, padx=5)
        
        # 新文件选择框
        new_frame = ttk.LabelFrame(self, text="新版本节点文件", padding=5)
        new_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.new_path = tk.StringVar()
        ttk.Entry(new_frame, textvariable=self.new_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(new_frame, text="选择文件", command=self.select_new_file).pack(side=tk.LEFT, padx=5)
        
        # 添加按钮框架
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=5)
        
        # 比较按钮
        self.compare_btn = ttk.Button(button_frame, text="比较节点", command=self.compare_nodes)
        self.compare_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加打开文件按钮（初始状态禁用）
        self.open_file_btn = ttk.Button(
            button_frame, 
            text="打开结果文件", 
            command=self.open_result_file,
            state=tk.DISABLED
        )
        self.open_file_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(self, text="比较结果", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.result_text = tk.Text(result_frame, height=15, width=60)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def select_old_file(self):
        """选择旧版本文件"""
        filename = filedialog.askopenfilename(
            title="选择旧版本节点文件",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            self.old_path.set(filename)
            
    def select_new_file(self):
        """选择新版本文件"""
        filename = filedialog.askopenfilename(
            title="选择新版本节点文件",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            self.new_path.set(filename)
            
    def compare_nodes(self):
        """比较节点"""
        if not self.old_path.get() or not self.new_path.get():
            messagebox.showerror("错误", "请选择要比较的文件！")
            return
            
        try:
            # 加载文件
            with open(self.old_path.get(), 'r', encoding='utf-8') as f:
                old_json = json.load(f)
            with open(self.new_path.get(), 'r', encoding='utf-8') as f:
                new_json = json.load(f)
                
            # 比较节点
            added_nodes, added_node_names = NodeDiffer.compare_nodes(old_json, new_json)
            
            # 显示结果
            self.result_text.delete('1.0', tk.END)
            if not added_nodes:
                self.result_text.insert(tk.END, "未发现新增节点。\n")
                self.open_file_btn.config(state=tk.DISABLED)  # 禁用打开按钮
                self.output_file = None
                return
                
            self.result_text.insert(tk.END, f"发现 {len(added_nodes)} 个新增节点：\n\n")
            for node_name in added_node_names:
                self.result_text.insert(tk.END, f"- {node_name}\n")
                
            # 保存新增节点
            output_dir = os.path.dirname(self.new_path.get())
            self.output_file = NodeDiffer.save_added_nodes(added_nodes, output_dir)
            
            if self.output_file:
                self.result_text.insert(tk.END, f"\n新增节点已保存到：\n{self.output_file}")
                self.open_file_btn.config(state=tk.NORMAL)  # 启用打开按钮
            else:
                self.open_file_btn.config(state=tk.DISABLED)  # 禁用打开按钮
                
        except Exception as e:
            messagebox.showerror("错误", f"比较失败：{str(e)}")
            self.open_file_btn.config(state=tk.DISABLED)  # 禁用打开按钮
            self.output_file = None
            
    def open_result_file(self):
        """打开结果文件"""
        if not self.output_file or not os.path.exists(self.output_file):
            messagebox.showerror("错误", "结果文件不存在！")
            return
            
        try:
            # 使用系统默认程序打开文件
            if sys.platform == 'win32':  # Windows
                os.startfile(self.output_file)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{self.output_file}"')
            else:  # Linux
                os.system(f'xdg-open "{self.output_file}"')
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败：{str(e)}")
