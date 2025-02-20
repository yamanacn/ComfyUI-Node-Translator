import ast
import os
import logging
import json
from typing import Dict, List, Optional
from src.file_utils import FileUtils

class NodeParser:
    """ComfyUI 节点解析器类
    
    用于解析 Python 文件中的 ComfyUI 节点定义,提取需要翻译的文本信息
    """

    def __init__(self, folder_path: str):
        """初始化节点解析器
        
        Args:
            folder_path: 要解析的文件夹路径
        """
        self.folder_path = folder_path
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dirs = FileUtils.init_output_dirs(self.base_path)

    def parse_file(self, file_path: str) -> Dict:
        """解析单个 Python 文件
        
        Args:
            file_path: Python 文件路径
            
        Returns:
            Dict: 解析出的节点信息字典
        """
        logging.info(f"开始解析文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 解析 Python 代码为 AST
        tree = ast.parse(content)
        nodes_info = {}
        
        # 首先获取映射信息
        node_mappings = {}  # 类名到节点名的映射
        display_names = {}  # 节点名到显示名的映射
        
        # 获取 NODE_CLASS_MAPPINGS 和 NODE_DISPLAY_NAME_MAPPINGS
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if 'NODE_CLASS_MAPPINGS' in targets and isinstance(node.value, ast.Dict):
                    # 修改这里的映射获取逻辑
                    for key, value in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Str) and isinstance(value, ast.Name):
                            # 反转映射关系：使用类名作为键，映射名作为值
                            class_name = value.id
                            mapped_name = key.s
                            node_mappings[class_name] = mapped_name
                            logging.debug(f"找到节点映射: {class_name} -> {mapped_name}")
                elif 'NODE_DISPLAY_NAME_MAPPINGS' in targets and isinstance(node.value, ast.Dict):
                    for key, value in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Str) and isinstance(value, ast.Str):
                            display_names[key.s] = value.s
                            logging.debug(f"找到显示名映射: {key.s} -> {value.s}")
        
        # 解析节点类
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                logging.debug(f"检查类: {node.name}")
                if self._is_comfy_node(node):
                    node_info = self._parse_node_class(node)
                    if node_info:
                        # 获取正确的节点名称
                        class_name = node.name
                        if class_name in node_mappings:
                            # 使用映射中定义的实际节点名
                            node_key = node_mappings[class_name]
                            # 获取显示名称
                            display_name = display_names.get(node_key, node_key)
                            logging.info(f"使用映射节点名: {node_key} (显示名称: {display_name})")
                        else:
                            # 如果没有映射，使用类名
                            node_key = class_name
                            display_name = class_name
                            logging.info(f"使用类名作为节点名: {node_key}")
                        
                        nodes_info[node_key] = {
                            "title": display_name,
                            "inputs": node_info.get("inputs", {}),
                            "widgets": node_info.get("widgets", {}),
                            "outputs": node_info.get("outputs", {})
                        }
                        
                        logging.info(f"成功解析节点: {node_key} (显示名称: {display_name})")
        
        logging.info(f"文件 {file_path} 解析完成，找到 {len(nodes_info)} 个节点")
        return nodes_info

    def _parse_node_class(self, class_node: ast.ClassDef) -> Optional[Dict]:
        """解析节点类定义
        
        Args:
            class_node: 类定义的 AST 节点
            
        Returns:
            Optional[Dict]: 节点信息字典,如果不是 ComfyUI 节点则返回 None
        """
        if not self._is_comfy_node(class_node):
            return None
            
        node_info = {
            'title': self._get_node_title(class_node),
            'inputs': {},
            'outputs': {},
            'widgets': {}
        }
        
        # 解析类中的方法和属性
        for item in class_node.body:
            # 检查 INPUT_TYPES 方法
            if isinstance(item, ast.FunctionDef) and item.name == 'INPUT_TYPES':
                # 检查是否是类方法
                if any(isinstance(decorator, ast.Name) and decorator.id == 'classmethod' 
                      for decorator in item.decorator_list):
                    parsed_types = self._parse_input_types_method(item)
                    if parsed_types:
                        # 更新输入
                        if 'inputs' in parsed_types:
                            node_info['inputs'].update(parsed_types['inputs'])
                        # 更新部件
                        if 'widgets' in parsed_types:
                            node_info['widgets'].update(parsed_types['widgets'])
            
            # 解析类属性
            elif isinstance(item, ast.Assign):
                targets = [t.id for t in item.targets if isinstance(t, ast.Name)]
                
                # 解析 RETURN_TYPES
                if 'RETURN_TYPES' in targets:
                    return_types = self._parse_return_types(item.value)
                    if return_types:
                        # 为每个返回类型创建默认输出名称
                        for i, return_type in enumerate(return_types):
                            node_info['outputs'][f'output_{i}'] = return_type
                
                # 解析 RETURN_NAMES
                elif 'RETURN_NAMES' in targets:
                    return_names = self._parse_return_names(item.value)
                    if return_names:
                        # 使用自定义名称替换默认输出名称
                        outputs = {}
                        for i, (name, type_) in enumerate(zip(return_names, node_info['outputs'].values())):
                            outputs[name] = type_
                        node_info['outputs'] = outputs
                        
                # 解析其他属性
                elif 'CATEGORY' in targets:
                    if isinstance(item.value, ast.Constant):
                        node_info['category'] = item.value.value
                elif 'FUNCTION' in targets:
                    if isinstance(item.value, ast.Constant):
                        node_info['function'] = item.value.value
                elif 'OUTPUT_NODE' in targets:
                    if isinstance(item.value, ast.Constant):
                        node_info['is_output'] = item.value.value
        
        return node_info

    def _is_comfy_node(self, class_node: ast.ClassDef) -> bool:
        """检查类是否是 ComfyUI 节点
        
        Args:
            class_node: 类定义的 AST 节点
            
        Returns:
            bool: 是否是 ComfyUI 节点
        """
        has_input_types = False
        has_return_types = False
        has_category = False
        has_function = False
        
        # 首先检查类方法
        for item in class_node.body:
            # 检查 INPUT_TYPES 方法
            if isinstance(item, ast.FunctionDef) and item.name == 'INPUT_TYPES':
                # 检查是否是类方法或普通方法
                if (any(isinstance(decorator, ast.Name) and decorator.id == 'classmethod' 
                      for decorator in item.decorator_list) or
                    item.name == 'INPUT_TYPES'):
                    has_input_types = True
                
            # 检查类属性
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == 'RETURN_TYPES':
                            has_return_types = True
                        elif target.id == 'CATEGORY':
                            has_category = True
                        elif target.id == 'FUNCTION':
                            has_function = True
        
        # 记录详细信息
        logging.debug(f"节点类 {class_node.name} 检查结果:")
        logging.debug(f"- INPUT_TYPES: {has_input_types}")
        logging.debug(f"- RETURN_TYPES: {has_return_types}")
        logging.debug(f"- CATEGORY: {has_category}")
        logging.debug(f"- FUNCTION: {has_function}")
        
        # 只要满足 INPUT_TYPES 和 RETURN_TYPES 中的一个就认为是节点
        is_node = has_input_types or has_return_types
        
        if is_node:
            logging.info(f"找到 ComfyUI 节点类: {class_node.name}")
        
        return is_node

    def _parse_input_types_method(self, method_node: ast.FunctionDef) -> Dict:
        """解析 INPUT_TYPES 方法，同时提取输入和部件信息
        
        Args:
            method_node: 方法的 AST 节点
            
        Returns:
            Dict: 包含 inputs 和 widgets 的字典
        """
        result = {
            'inputs': {},
            'widgets': {}
        }
        
        # 查找 return 语句
        for node in ast.walk(method_node):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                # 解析返回的字典
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant):
                        section_name = key.value  # required, optional, hidden
                        if isinstance(value, ast.Dict):
                            # 解析每个输入/部件定义
                            for item_key, item_value in zip(value.keys, value.values):
                                if isinstance(item_key, ast.Constant):
                                    item_name = item_key.value
                                    # 解析类型元组
                                    if isinstance(item_value, ast.Tuple):
                                        type_info = self._parse_type_tuple(item_value)
                                        # 根据类型判断是输入还是部件
                                        if self._is_widget_type(type_info['type']):
                                            result['widgets'][item_name] = type_info['type']
                                        else:
                                            # 对于输入，保留原始名称
                                            if section_name in ['required', 'optional', 'hidden']:
                                                result['inputs'][item_name] = item_name
        
        return result

    def _parse_type_tuple(self, tuple_node: ast.Tuple) -> Dict:
        """解析类型元组，提取类型和参数信息
        
        Args:
            tuple_node: 元组的 AST 节点
            
        Returns:
            Dict: 包含类型和参数的字典
        """
        type_info = {
            'type': 'UNKNOWN',
            'params': {}
        }
        
        if len(tuple_node.elts) > 0:
            # 解析类型
            first_element = tuple_node.elts[0]
            if isinstance(first_element, ast.Constant):
                type_info['type'] = first_element.value
            elif isinstance(first_element, ast.Name):
                type_info['type'] = first_element.id
            
            # 解析参数（如果有）
            if len(tuple_node.elts) > 1:
                second_element = tuple_node.elts[1]
                if isinstance(second_element, ast.Dict):
                    for key, value in zip(second_element.keys, second_element.values):
                        if isinstance(key, ast.Constant):
                            param_name = key.value
                            if isinstance(value, ast.Constant):
                                type_info['params'][param_name] = value.value
        
        return type_info

    def _is_widget_type(self, type_name: str) -> bool:
        """判断类型是否是部件类型
        
        Args:
            type_name: 类型名称
            
        Returns:
            bool: 是否是部件类型
        """
        widget_types = {
            'INT', 'FLOAT', 'STRING', 'BOOLEAN', 
            'COMBO', 'DROPDOWN', 'TEXT', 'TEXTAREA',
            'SLIDER', 'CHECKBOX', 'COLOR', 'RADIO',
            'SELECT', 'NUMBER'
        }
        
        # 添加一些常见的输入类型
        input_types = {
            'IMAGE', 'LATENT', 'MODEL', 'VAE', 'CLIP', 
            'CONDITIONING', 'MASK', 'STYLE_MODEL',
            'CONTROL_NET', 'BBOX', 'SEGS'
        }
        
        return (type_name.upper() in widget_types and 
                type_name.upper() not in input_types)

    def _parse_return_types(self, value_node: ast.AST) -> List[str]:
        """解析 RETURN_TYPES 定义
        
        Args:
            value_node: 值的 AST 节点
            
        Returns:
            List[str]: 返回类型列表
        """
        return_types = []
        
        if isinstance(value_node, (ast.Tuple, ast.List)):
            for element in value_node.elts:
                if isinstance(element, ast.Constant):
                    return_types.append(element.value)
                elif isinstance(element, ast.Name):
                    return_types.append(element.id)
                
        return return_types

    def _parse_return_names(self, value_node: ast.AST) -> List[str]:
        """解析 RETURN_NAMES 定义
        
        Args:
            value_node: 值的 AST 节点
            
        Returns:
            List[str]: 返回名称列表
        """
        return_names = []
        
        if isinstance(value_node, (ast.Tuple, ast.List)):
            for element in value_node.elts:
                if isinstance(element, ast.Constant):
                    return_names.append(element.value)
                
        return return_names

    def _get_node_title(self, class_node: ast.ClassDef) -> str:
        """获取节点的显示标题
        
        Args:
            class_node: 类定义的 AST 节点
            
        Returns:
            str: 节点标题
        """
        # 首先查找 NODE_NAME 属性
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                targets = [t.id for t in item.targets if isinstance(t, ast.Name)]
                if 'NODE_NAME' in targets and isinstance(item.value, ast.Str):
                    return item.value.s
                    
        # 如果没有 NODE_NAME 属性,使用类名
        return class_node.name

    def _parse_widgets(self, node_class) -> Dict:
        """解析节点的部件信息
        
        Args:
            node_class: 节点类
            
        Returns:
            Dict: 部件信息字典
        """
        widgets = {}
        
        # 检查类是否有 REQUIRED 属性
        if hasattr(node_class, 'REQUIRED'):
            required = node_class.REQUIRED
            # 遍历所有必需的部件
            for widget_name, widget_type in required.items():
                # 使用原始的部件名称作为值，而不是类型
                widgets[widget_name] = widget_name
                
        # 检查类是否有 OPTIONAL 属性
        if hasattr(node_class, 'OPTIONAL'):
            optional = node_class.OPTIONAL
            # 遍历所有可选的部件
            for widget_name, widget_type in optional.items():
                # 使用原始的部件名称作为值，而不是类型
                widgets[widget_name] = widget_name
                
        return widgets

    def _parse_inputs(self, node_class) -> Dict:
        """解析节点的输入信息
        
        Args:
            node_class: 节点类
            
        Returns:
            Dict: 输入信息字典
        """
        inputs = {}
        
        # 检查类是否有 INPUT_TYPES 属性
        if hasattr(node_class, 'INPUT_TYPES'):
            input_types = node_class.INPUT_TYPES
            # 如果 INPUT_TYPES 是一个字典
            if isinstance(input_types, dict) and 'required' in input_types:
                required = input_types['required']
                # 遍历所有必需的输入
                for input_name, input_type in required.items():
                    # 使用原始的输入名称作为值
                    inputs[input_name] = input_name
                    
        return inputs

    def _parse_outputs(self, node_class) -> Dict:
        """解析节点的输出信息
        
        Args:
            node_class: 节点类
            
        Returns:
            Dict: 输出信息字典
        """
        outputs = {}
        
        # 检查类是否有 RETURN_TYPES 属性
        if hasattr(node_class, 'RETURN_TYPES'):
            return_types = node_class.RETURN_TYPES
            # 遍历所有输出类型
            for i, output_type in enumerate(return_types):
                output_name = f"output_{i}"
                # 使用原始的输出名称作为值
                outputs[output_name] = output_name
                
        return outputs

    def optimize_node_info(self, nodes_info: Dict) -> Dict:
        """优化节点信息，处理特殊的键值情况并规范化格式
        
        Args:
            nodes_info: 原始节点信息字典
            
        Returns:
            Dict: 优化后的节点信息字典
        """
        optimized = {}
        
        # 定义需要替换的类型
        type_replacements = {
            'INT': True,
            'FLOAT': True,
            'BOOL': True,
            'STRING': True,
            'NUMBER': True,
            'BOOLEAN': True
        }
        
        # 定义字段顺序
        field_order = ['title', 'inputs', 'widgets', 'outputs']
        
        for node_name, node_info in nodes_info.items():
            # 创建一个有序字典来保持字段顺序
            optimized_node = {}
            
            # 按照指定顺序添加字段
            for field in field_order:
                if field == 'title':
                    optimized_node['title'] = node_info.get('title', '')
                elif field == 'inputs':
                    optimized_node['inputs'] = {}
                    for input_name, input_value in node_info.get('inputs', {}).items():
                        if input_value in type_replacements:
                            optimized_node['inputs'][input_name] = input_name
                        else:
                            optimized_node['inputs'][input_name] = input_value
                elif field == 'widgets':
                    optimized_node['widgets'] = {}
                    for widget_name, widget_value in node_info.get('widgets', {}).items():
                        if widget_value in type_replacements:
                            optimized_node['widgets'][widget_name] = widget_name
                        else:
                            optimized_node['widgets'][widget_name] = widget_value
                elif field == 'outputs':
                    optimized_node['outputs'] = {}
                    for output_name, output_value in node_info.get('outputs', {}).items():
                        if output_value in type_replacements:
                            optimized_node['outputs'][output_name] = output_name
                        else:
                            optimized_node['outputs'][output_name] = output_value
            
            optimized[node_name] = optimized_node
        
        return optimized

    def parse_folder(self, folder_path: str) -> Dict:
        """解析文件夹中的所有 Python 文件"""
        all_nodes = {}
        
        # 获取插件专属的输出目录
        self.plugin_dirs = FileUtils.get_plugin_output_dir(self.base_path, folder_path)
        
        debug_info = {
            "total_files": 0,
            "processed_files": 0,
            "found_nodes": 0,
            "file_details": []
        }
        
        # 扫描 Python 文件
        try:
            py_files = FileUtils.scan_python_files(folder_path)
            debug_info["total_files"] = len(py_files)
            logging.info(f"找到 {len(py_files)} 个 Python 文件")
        except Exception as e:
            logging.error(f"扫描文件夹失败: {str(e)}")
            return {}
        
        # 解析每个文件
        for file_path in py_files:
            try:
                logging.info(f"正在解析文件: {file_path}")
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 解析文件
                nodes = self.parse_file(file_path)
                
                # 记录文件信息
                file_info = {
                    "file": file_path,
                    "nodes_found": len(nodes) if nodes else 0,
                    "node_names": list(nodes.keys()) if nodes else []
                }
                debug_info["file_details"].append(file_info)
                
                if nodes:
                    debug_info["found_nodes"] += len(nodes)
                    all_nodes.update(nodes)
                    logging.info(f"从文件 {file_path} 中解析出 {len(nodes)} 个节点: {list(nodes.keys())}")
                else:
                    logging.info(f"文件 {file_path} 中未找到节点")
                    
                debug_info["processed_files"] += 1
                
            except Exception as e:
                logging.error(f"解析文件失败 {file_path}: {str(e)}")
                debug_info["file_details"].append({
                    "file": file_path,
                    "error": str(e)
                })
                continue
        
        # 保存调试信息
        debug_file = os.path.join(self.plugin_dirs["debug"], "node_detection_debug.json")
        try:
            FileUtils.save_json(debug_info, debug_file)
            logging.info(f"调试信息已保存到: {debug_file}")
        except Exception as e:
            logging.error(f"保存调试信息失败: {str(e)}")
        
        # 优化节点信息
        try:
            optimized_nodes = self.optimize_node_info(all_nodes)
            logging.info(f"成功优化 {len(optimized_nodes)} 个节点的信息")
            return optimized_nodes
        except Exception as e:
            logging.error(f"优化节点信息失败: {str(e)}")
            return all_nodes 