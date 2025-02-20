import json
import os
from typing import Dict, Tuple, List

class NodeDiffer:
    """节点差异分析器"""
    
    @staticmethod
    def _normalize_node_name(node_name: str) -> str:
        """规范化节点名称
        
        例如：
        "LayerUtility: Llama Vision" -> "LayerUtility: LlamaVision"
        "LayerMask: Mask Edge Ultra Detail V2" -> "LayerMask: MaskEdgeUltraDetailV2"
        
        Args:
            node_name: 原始节点名称
            
        Returns:
            str: 规范化后的名称
        """
        # 分割前缀和后缀
        if ":" in node_name:
            prefix, suffix = node_name.split(":", 1)
            prefix = prefix.strip()
            suffix = suffix.strip()
            
            # 特殊处理规则
            special_cases = {
                "Llama Vision": "LlamaVision",
                "BiRefNet Ultra": "BiRefNetUltra",
                "Ben Ultra": "BenUltra",
                "Florence2 Ultra": "Florence2Ultra",
                "SAM2 Ultra": "SAM2Ultra",
                "SAM2 Video Ultra": "SAM2VideoUltra",
                "EVF-SAM Ultra": "EVFSAMUltra",
                "Transparent Background Ultra": "TransparentBackgroundUltra",
                "Human Parts Ultra": "HumanPartsUltra",
                "Mask Edge Ultra Detail": "MaskEdgeUltraDetail"
            }
            
            # 处理后缀部分
            words = suffix.split()
            processed_words = []
            i = 0
            while i < len(words):
                # 检查是否是特殊情况
                found = False
                for case, replacement in special_cases.items():
                    case_words = case.split()
                    if i + len(case_words) <= len(words):
                        if " ".join(words[i:i+len(case_words)]) == case:
                            processed_words.append(replacement)
                            i += len(case_words)
                            found = True
                            break
                
                if not found:
                    # 处理版本号
                    if words[i].startswith("V") and words[i][1:].isdigit():
                        processed_words.append(words[i])  # 保持版本号格式
                    else:
                        # 其他情况，移除空格并连接单词
                        processed_words.append(words[i])
                    i += 1
            
            # 连接处理后的单词
            normalized_suffix = "".join(processed_words)
            
            # 重新组合，保持冒号后的空格
            return f"{prefix}: {normalized_suffix}"
        
        return node_name
    
    @staticmethod
    def _get_base_name(node_name: str) -> str:
        """获取节点的基础名称
        
        例如：
        "LayerFilter: ChannelShake" -> "LayerFilter ChannelShake"
        
        Args:
            node_name: 完整节点名称
            
        Returns:
            str: 基础名称
        """
        # 首先规范化节点名称
        normalized_name = NodeDiffer._normalize_node_name(node_name)
        # 移除所有标点符号和多余空格
        name = normalized_name.replace(":", " ").replace("-", " ").replace("_", " ")
        # 分割成单词并重新组合
        words = [word.strip() for word in name.split() if word.strip()]
        return " ".join(words)
    
    @staticmethod
    def compare_nodes(old_json: Dict, new_json: Dict) -> Tuple[Dict, List[str]]:
        """比较两个节点文件，找出新增的节点"""
        added_nodes = {}
        added_node_names = []
        
        # 创建旧节点的基础名称集合
        old_base_names = {NodeDiffer._get_base_name(name) for name in old_json.keys()}
        
        # 遍历新文件中的所有节点
        for new_name, new_data in new_json.items():
            # 规范化节点名称
            normalized_name = NodeDiffer._normalize_node_name(new_name)
            # 获取新节点的基础名称
            new_base_name = NodeDiffer._get_base_name(normalized_name)
            
            # 如果基础名称不在旧节点中，认为是新增的
            if new_base_name not in old_base_names:
                # 使用规范化后的名称保存节点
                added_nodes[normalized_name] = new_data
                added_node_names.append(normalized_name)
                
        return added_nodes, added_node_names
    
    @staticmethod
    def normalize_json_content(json_data: Dict) -> Dict:
        """规范化 JSON 内容中的节点名称
        
        Args:
            json_data: 原始 JSON 数据
            
        Returns:
            Dict: 规范化后的 JSON 数据
        """
        normalized_data = {}
        
        # 遍历所有节点
        for node_name, node_data in json_data.items():
            # 规范化节点名称
            normalized_name = NodeDiffer._normalize_node_name(node_name)
            normalized_data[normalized_name] = node_data
            
        return normalized_data
    
    @staticmethod
    def save_added_nodes(added_nodes: Dict, output_path: str) -> str:
        """保存新增节点到文件"""
        if not added_nodes:
            return ""
            
        # 规范化节点名称
        normalized_nodes = NodeDiffer.normalize_json_content(added_nodes)
        
        output_file = os.path.join(output_path, "added_nodes.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(normalized_nodes, f, indent=4, ensure_ascii=False)
            
        return output_file 