import os
from typing import Dict, List
from openai import OpenAI
import requests
import json
import time
from .prompts import PromptTemplate  # 导入提示词模板
from .translation_config import TranslationConfig
import glob
from .file_utils import FileUtils

class Translator:
    """节点翻译器类
    
    负责调用火山引擎 API 将节点信息翻译成中文
    """
    
    def __init__(self, api_key: str, model_id: str):
        """初始化翻译器
        
        Args:
            api_key: API 密钥
            model_id: 火山引擎模型 ID
        """
        self.model_id = model_id
        
        # 获取程序根目录
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 初始化输出目录
        self.dirs = FileUtils.init_output_dirs(self.base_path)
        
        # 从提示词模板获取系统提示词
        self.system_prompt = PromptTemplate.get_translator_prompt()
        
        # 初始化火山引擎客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        
        # 创建工作目录
        self.work_dir = os.path.join(self.dirs["temp"], "workspace")
        os.makedirs(self.work_dir, exist_ok=True)
        
        self.total_prompt_tokens = 0    # 输入 tokens
        self.total_completion_tokens = 0 # 输出 tokens
        self.total_tokens = 0           # 总 tokens

    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            # 从模板获取火山引擎提示词
            system_prompt = PromptTemplate.get_test_prompt()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "你好，请回复一句话。"}
            ]
            
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=0.1,
                top_p=0.95,
                stream=False,
                max_tokens=100,
                presence_penalty=0,
                frequency_penalty=0
            )
            
            # 检查响应
            if completion.choices and completion.choices[0].message:
                return True
            else:
                raise Exception("API 响应格式不正确")
                
        except Exception as e:
            # 解析错误信息
            error_msg = str(e)
            if "AccountOverdueError" in error_msg:
                raise Exception("账户余额不足，请充值后重试")
            elif "InvalidApiKeyError" in error_msg:
                raise Exception("API 密钥无效")
            elif "ModelNotFoundError" in error_msg:
                raise Exception("模型 ID 无效")
            else:
                raise Exception(f"API 连接测试失败: {error_msg}")

    def translate_batch(self, batch_nodes: Dict) -> Dict:
        """翻译一批节点"""
        try:
            # 构建提示词
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": json.dumps(batch_nodes, ensure_ascii=False, indent=2)}
            ]
            
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=0.1,  # 降低随机性，保持翻译一致性
                top_p=0.95,
                stream=False,
                max_tokens=4096,
                presence_penalty=0,
                frequency_penalty=0,
                stop=None,
                user="comfyui-translator"
            )
            
            # 解析返回结果
            response_text = completion.choices[0].message.content
            
            try:
                translated_nodes = json.loads(response_text)
                return translated_nodes
            except json.JSONDecodeError:
                raise Exception(f"翻译结果不是有效的 JSON 格式: {response_text}")
            
        except Exception as e:
            raise Exception(f"翻译失败: {str(e)}")

    def translate_nodes(self, nodes_info: Dict, folder_path: str, batch_size: int = 6, update_progress=None) -> Dict:
        """翻译节点信息"""
        temp_files = []  # 记录所有临时文件
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        try:
            # 获取插件专属的输出目录
            plugin_dirs = FileUtils.get_plugin_output_dir(self.base_path, folder_path)
            
            # 保存原始待翻译文件
            original_file = os.path.join(plugin_dirs["temp"], "nodes_to_translate.json")
            FileUtils.save_json(nodes_info, original_file)
            temp_files.append(original_file)
            
            if update_progress:
                update_progress(0, f"[准备] 保存原始节点信息到: {original_file}")
            
            all_translated_nodes = {}
            
            # 分批处理节点
            node_items = list(nodes_info.items())
            total_batches = (len(node_items) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, len(node_items))
                current_batch = dict(node_items[start_idx:end_idx])
                
                # 更新进度
                if update_progress:
                    progress = int((batch_idx / total_batches) * 100)
                    node_names = list(current_batch.keys())
                    update_progress(progress, f"[翻译] 第 {batch_idx + 1}/{total_batches} 批: {', '.join(node_names)}")
                
                try:
                    # 1. 翻译当前批次
                    batch_translated = self._translate_batch(current_batch, update_progress, progress)
                    
                    # 2. 验证和修正翻译结果
                    if update_progress:
                        update_progress(progress, "[验证] 正在验证翻译结果...")
                        
                    batch_corrected = self._validate_and_correct_batch(
                        current_batch,
                        batch_translated,
                        update_progress,
                        progress
                    )
                    
                    # 3. 保存已修正的批次
                    batch_file = os.path.join(
                        plugin_dirs["translations"], 
                        f"batch_{batch_idx + 1}_translated.json"
                    )
                    FileUtils.save_json(batch_corrected, batch_file)
                    temp_files.append(batch_file)  # 记录临时文件
                    
                    # 4. 更新总结果
                    all_translated_nodes.update(batch_corrected)
                    
                    if update_progress:
                        update_progress(progress, f"[完成] 批次 {batch_idx + 1} 的处理已完成")
                    
                except Exception as e:
                    if update_progress:
                        update_progress(progress, f"[错误] 批次 {batch_idx + 1} 处理失败: {str(e)}")
                    raise
            
            # 保存最终结果
            plugin_name = os.path.basename(folder_path.rstrip(os.path.sep))
            final_file = os.path.join(plugin_dirs["translations"], f"{plugin_name}.json")
            
            # 最终验证
            if update_progress:
                update_progress(95, "[验证] 进行最终验证...")
            final_corrected = self._final_validation(
                nodes_info,
                all_translated_nodes,
                update_progress
            )
            
            # 保存最终结果
            FileUtils.save_json(final_corrected, final_file)
            
            # 清理临时文件
            self._cleanup_temp_files(temp_files, update_progress)
            
            # 在完成时显示总计信息
            if update_progress:
                # 计算费用（火山引擎费率：输入 0.0008元/千tokens，输出 0.0020元/千tokens）
                prompt_cost = (self.total_prompt_tokens / 1000) * 0.0008
                completion_cost = (self.total_completion_tokens / 1000) * 0.0020
                total_cost = prompt_cost + completion_cost
                
                update_progress(100, f"[完成] 翻译和验证完成！")
                update_progress(100, f"[统计] 总计使用 {self.total_tokens} tokens:")
                update_progress(100, f"       - 输入: {self.total_prompt_tokens} tokens (¥{prompt_cost:.4f})")
                update_progress(100, f"       - 输出: {self.total_completion_tokens} tokens (¥{completion_cost:.4f})")
                update_progress(100, f"[费用] 预估总费用（请以实际为准）: ¥{total_cost:.4f}")
            
            return final_corrected
            
        except Exception as e:
            # 发生错误时清理临时文件
            self._cleanup_temp_files(temp_files, update_progress)
            
            # 解析错误信息
            error_msg = str(e)
            if "AccountOverdueError" in error_msg:
                if update_progress:
                    update_progress(-1, "[错误] 账户余额不足，请充值后重试")
            elif "InvalidApiKeyError" in error_msg:
                if update_progress:
                    update_progress(-1, "[错误] API 密钥无效")
            elif "ModelNotFoundError" in error_msg:
                if update_progress:
                    update_progress(-1, "[错误] 模型 ID 无效")
            else:
                if update_progress:
                    update_progress(-1, f"[错误] 翻译过程出错: {error_msg}")
            raise

    def _validate_and_correct_batch(self, original_batch: Dict, translated_batch: Dict, 
                                  update_progress=None, progress: int = 0) -> Dict:
        """验证和修正单个批次的翻译结果"""
        corrected_batch = {}
        
        for node_name, node_info in original_batch.items():
            if node_name not in translated_batch:
                if update_progress:
                    update_progress(progress, f"[修正] 节点 {node_name} 未翻译，使用原始数据")
                corrected_batch[node_name] = node_info
                continue
            
            translated_info = translated_batch[node_name]
            corrected_node = {
                "title": translated_info.get("title", node_info.get("title", "")),
                "inputs": {},
                "widgets": {},
                "outputs": {}
            }
            
            # 验证和修正每个部分
            for section in ["inputs", "widgets", "outputs"]:
                orig_section = node_info.get(section, {})
                trans_section = translated_info.get(section, {})
                
                # 确保所有原始键都存在
                for key in orig_section:
                    if key in trans_section:
                        corrected_node[section][key] = trans_section[key]
                    else:
                        if update_progress:
                            update_progress(progress, f"[修正] 节点 {node_name} 的 {section} 中缺少键 {key}")
                        corrected_node[section][key] = key
            
            corrected_batch[node_name] = corrected_node
        
        return corrected_batch

    def _final_validation(self, original_nodes: Dict, translated_nodes: Dict, 
                         update_progress=None) -> Dict:
        """最终验证，确保所有节点都被正确翻译"""
        final_nodes = {}
        
        # 检查所有原始节点是否都被翻译
        for node_name, node_info in original_nodes.items():
            if node_name not in translated_nodes:
                if update_progress:
                    update_progress(95, f"[修正] 节点 {node_name} 未翻译，使用原始数据")
                final_nodes[node_name] = node_info
                continue
            
            translated_info = translated_nodes[node_name]
            
            # 验证必要字段
            if not all(field in translated_info for field in ["title", "inputs", "widgets", "outputs"]):
                if update_progress:
                    update_progress(96, f"[修正] 节点 {node_name} 缺少必要字段，使用原始数据")
                final_nodes[node_name] = node_info
                continue
            
            # 验证字段内容
            final_nodes[node_name] = translated_info
        
        return final_nodes

    def _translate_batch(self, current_batch: Dict, update_progress=None, progress=0) -> Dict:
        """翻译单个批次
        
        Args:
            current_batch: 当前批次的数据
            update_progress: 进度更新回调函数
            progress: 当前进度
            
        Returns:
            Dict: 翻译后的节点信息
        """
        translated_text = ""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请翻译以下节点信息:\n{json.dumps(current_batch, indent=2, ensure_ascii=False)}"}
        ]
        
        completion = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "text"},
            top_p=0.95,
            presence_penalty=0,
            timeout=30  # deepseek 可能需要更长的响应时间
        )
        
        # deepseek 模型可能会返回 reasoning_content
        if hasattr(completion.choices[0].message, 'reasoning_content'):
            if update_progress:
                update_progress(progress, f"DeepSeek 思考过程: {completion.choices[0].message.reasoning_content}")
        
        # 累计 tokens 使用量
        if hasattr(completion, 'usage'):
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            batch_tokens = completion.usage.total_tokens
            
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += batch_tokens
            
            if update_progress:
                update_progress(progress, 
                    f"[统计] 当前批次使用 {batch_tokens} tokens "
                    f"(输入: {prompt_tokens}, 输出: {completion_tokens}), "
                    f"累计: {self.total_tokens} tokens"
                )
        
        translated_text = completion.choices[0].message.content
        
        # 检查响应内容
        if not translated_text or len(translated_text) < 10:
            raise Exception("API 响应内容异常")
        
        # 提取 JSON 内容
        json_start = translated_text.find('{')
        json_end = translated_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_content = translated_text[json_start:json_end]
            batch_translated = json.loads(json_content)
            
            return batch_translated
        
        raise Exception("API 响应格式不正确")

    def _validate_batch_files(self, source_file: str, translated_file: str) -> tuple[bool, Dict, str]:
        """通过三步校对修正流程处理翻译结果，并生成详细日志"""
        try:
            # 读取文件
            with open(source_file, 'r', encoding='utf-8') as f:
                original_batch = json.load(f)
            with open(translated_file, 'r', encoding='utf-8') as f:
                translated_batch = json.load(f)
            
            batch_num = os.path.basename(translated_file).split('_')[1]
            log_entries = []
            log_entries.append(f"批次 {batch_num} 校验修正日志")
            log_entries.append("=" * 50)
            
            # 第一步：建立标准映射关系
            from .translation_config import TranslationConfig
            standard_translations = {
                **TranslationConfig.COMMON_TRANSLATIONS,
                **TranslationConfig.BODY_PART_TRANSLATIONS
            }
            
            # 第二步：修正所有节点
            corrected_batch = {}
            log_entries.append("\n节点修正")
            log_entries.append("-" * 30)
            
            for node_name, node_data in original_batch.items():
                log_entries.append(f"\n节点: {node_name}")
                corrected_node = {
                    "title": translated_batch[node_name]["title"] if node_name in translated_batch else node_data["title"],
                    "inputs": {},
                    "outputs": {},
                    "widgets": {}
                }
                
                # 处理每个部分
                for section in ["inputs", "outputs", "widgets"]:
                    if section in node_data:
                        log_entries.append(f"\n{section}:")
                        
                        # 获取原始数据和翻译后的数据
                        orig_section = node_data[section]
                        trans_section = translated_batch.get(node_name, {}).get(section, {})
                        
                        # 使用原始文件中的键
                        for orig_key in orig_section.keys():
                            # 1. 如果是特殊类型值，保持不变
                            if orig_key.upper() in TranslationConfig.PRESERVED_TYPES:
                                corrected_node[section][orig_key] = orig_key.upper()
                                log_entries.append(f"保留特殊类型: {orig_key}")
                                continue
                            
                            # 2. 如果在标准映射中存在对应的翻译
                            if orig_key.lower() in standard_translations:
                                corrected_node[section][orig_key] = standard_translations[orig_key.lower()]
                                log_entries.append(f"使用标准映射: {orig_key} -> {standard_translations[orig_key.lower()]}")
                                continue
                            
                            # 3. 如果在翻译后的数据中有对应的中文值
                            if orig_key in trans_section:
                                trans_value = trans_section[orig_key]
                                # 如果值是中文，使用它
                                if any('\u4e00' <= char <= '\u9fff' for char in str(trans_value)):
                                    corrected_node[section][orig_key] = trans_value
                                    log_entries.append(f"使用翻译值: {orig_key} -> {trans_value}")
                                    continue
                        
                            # 4. 如果都没有找到合适的翻译，保持原值
                            corrected_node[section][orig_key] = orig_key
                            log_entries.append(f"保持原值: {orig_key}")
                
                corrected_batch[node_name] = corrected_node
            
            # 保存修正后的结果
            corrected_file = os.path.join(self.dirs["temp"], f"batch_{batch_num}_corrected.json")
            FileUtils.save_json(corrected_batch, corrected_file)
            
            # 保存详细日志
            log_file = os.path.join(self.dirs["logs"], 
                                  f"batch_{batch_num}_correction_log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_entries))
            
            return True, corrected_batch, '\n'.join(log_entries)
            
        except Exception as e:
            return False, translated_batch, f"修正过程出错: {str(e)}"

    def _is_valid_translation(self, english_key: str, chinese_text: str) -> bool:
        """检查中文文本是否是英文键的合理翻译
        
        Args:
            english_key: 英文键名
            chinese_text: 中文文本
            
        Returns:
            bool: 是否是合理的翻译
        """
        # 定义常见翻译对照
        translations = {
            'image': {'图像', '图片'},
            'mask': {'遮罩', '掩码', '蒙版'},
            'model': {'模型'},
            'processor': {'处理器'},
            'device': {'设备'},
            'bbox': {'边界框', '边框'},
            'samples': {'样本'},
            'operation': {'操作'},
            'guide': {'引导图'},
            'radius': {'半径'},
            'epsilon': {'epsilon', 'eps'},
            'threshold': {'阈值'},
            'contrast': {'对比度'},
            'brightness': {'亮度'},
            'saturation': {'饱和度'},
            'hue': {'色调'},
            'gamma': {'伽马'}
        }
        
        return chinese_text in translations.get(english_key, set())

    def _final_validate_and_correct(self, original_file: str, final_translated_file: str) -> tuple[bool, Dict, str]:
        """最终校验和修正，通过建立中英文映射关系来修正键名"""
        try:
            # 读取文件
            with open(original_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            with open(final_translated_file, 'r', encoding='utf-8') as f:
                translated_data = json.load(f)
            
            log_entries = []
            log_entries.append("\n=== 最终校验修正日志 ===")
            log_entries.append(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            log_entries.append("=" * 50)
            
            # 第一步：建立中英文双向映射
            en_to_cn = {}  # 英文到中文的映射
            cn_to_en = {}  # 中文到英文的映射
            log_entries.append("\n第一步：建立中英文映射关系")
            
            # 1.1 首先从原始文件中获取所有英文键
            for node_name, node_data in original_data.items():
                for section in ["inputs", "outputs", "widgets"]:
                    if section in node_data:
                        for key, value in node_data[section].items():
                            # 如果原始文件中键和值相同，这个键就是标准英文键
                            if key == value:
                                # 在翻译后的文件中查找对应的中文值
                                if (node_name in translated_data and 
                                    section in translated_data[node_name]):
                                    trans_section = translated_data[node_name][section]
                                    # 如果找到了这个键对应的中文值
                                    if key in trans_section:
                                        trans_value = trans_section[key]
                                        if any('\u4e00' <= char <= '\u9fff' for char in str(trans_value)):
                                            en_to_cn[key] = trans_value
                                            cn_to_en[trans_value] = key
                                            log_entries.append(f"从原始文件映射: {key} <-> {trans_value}")
            
            # 1.2 从翻译后的文件中收集其他映射关系
            for node_name, node_data in translated_data.items():
                for section in ["inputs", "outputs", "widgets"]:
                    if section in node_data:
                        for key, value in node_data[section].items():
                            # 如果值是中文且键是英文
                            if (any('\u4e00' <= char <= '\u9fff' for char in str(value)) and
                                not any('\u4e00' <= char <= '\u9fff' for char in str(key))):
                                en_to_cn[key] = value
                                cn_to_en[value] = key
                                log_entries.append(f"从翻译文件映射: {key} <-> {value}")
                            # 如果键是中文且值是英文
                            elif (any('\u4e00' <= char <= '\u9fff' for char in str(key)) and
                                  not any('\u4e00' <= char <= '\u9fff' for char in str(value))):
                                cn_to_en[key] = value
                                en_to_cn[value] = key
                                log_entries.append(f"从翻译文件映射: {value} <-> {key}")
            
            # 第二步：修正所有节点
            final_corrected = {}
            corrections_made = False
            log_entries.append("\n第二步：应用修正")
            
            for node_name, node_data in translated_data.items():
                corrected_node = {
                    "title": node_data["title"],
                    "inputs": {},
                    "outputs": {},
                    "widgets": {}
                }
                
                # 获取原始节点数据
                orig_node = original_data.get(node_name, {})
                
                # 处理每个部分
                for section in ["inputs", "outputs", "widgets"]:
                    if section in node_data:
                        # 获取原始部分的键
                        orig_keys = orig_node.get(section, {}).keys()
                        
                        for key, value in node_data[section].items():
                            # 如果键是中文，需要修正
                            if any('\u4e00' <= char <= '\u9fff' for char in str(key)):
                                if key in cn_to_en:
                                    eng_key = cn_to_en[key]
                                    # 验证这个英文键是否在原始数据中
                                    if eng_key in orig_keys:
                                        corrected_node[section][eng_key] = value
                                        corrections_made = True
                                        log_entries.append(f"修正键: {key} -> {eng_key}")
                                    else:
                                        # 如果不在原始数据中，尝试查找原始键
                                        for orig_key in orig_keys:
                                            if orig_key.lower() == eng_key.lower():
                                                corrected_node[section][orig_key] = value
                                                corrections_made = True
                                                log_entries.append(f"修正键(使用原始大小写): {key} -> {orig_key}")
                                                break
                                else:
                                    # 在原始数据中查找对应的英文键
                                    found = False
                                    for orig_key in orig_keys:
                                        if orig_key in en_to_cn and en_to_cn[orig_key] == key:
                                            corrected_node[section][orig_key] = value
                                            corrections_made = True
                                            log_entries.append(f"修正键(从原始数据): {key} -> {orig_key}")
                                            found = True
                                            break
                                    if not found:
                                        log_entries.append(f"警告: 未找到键 '{key}' 的英文映射")
                                        # 保持原样
                                        corrected_node[section][key] = value
                            else:
                                corrected_node[section][key] = value
                
                final_corrected[node_name] = corrected_node
            
            # 保存映射关系
            mapping_file = os.path.join(self.dirs["temp"], "translation_mapping.json")
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "en_to_cn": en_to_cn,
                    "cn_to_en": cn_to_en
                }, f, indent=4, ensure_ascii=False)
            
            # 保存详细日志
            log_file = os.path.join(self.dirs["logs"], 
                                  f"final_correction_log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
            log_content = '\n'.join(log_entries)
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            # 如果进行了修正，保存结果
            if corrections_made:
                output_file = os.path.join(self.dirs["temp"], "final_corrected.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(final_corrected, f, indent=4, ensure_ascii=False)
            
            return not corrections_made, final_corrected, log_content
            
        except Exception as e:
            error_msg = f"最终校验修正失败: {str(e)}"
            return False, translated_data, error_msg 

    def _cleanup_temp_files(self, temp_files: List[str], update_progress=None):
        """清理临时文件
        
        Args:
            temp_files: 临时文件路径列表
            update_progress: 进度更新回调函数
        """
        if not temp_files:
            return
        
        if update_progress:
            update_progress(97, "[清理] 开始清理临时文件...")
        
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    if update_progress:
                        update_progress(98, f"[清理] 已删除: {os.path.basename(file_path)}")
            except Exception as e:
                if update_progress:
                    update_progress(98, f"[警告] 清理文件失败: {os.path.basename(file_path)} ({str(e)})")
        
        if update_progress:
            update_progress(99, "[清理] 临时文件清理完成") 