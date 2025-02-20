"""提示词模板管理模块"""

# 通用的翻译助手提示词
TRANSLATOR_PROMPT = """你是一个专业的 ComfyUI 节点翻译助手。请遵循以下规则:

严格遵循规则： 保持 JSON 格式不变,只翻译右侧值为中文

2. 节点标题翻译规则:
   - 保留功能类型标识，如 "While循环-起始"、"While循环-结束"
   - 对于版本标识，保持原样，如 "V2"、"SDXL"、 "Ultra"等
   - 对于功能组合词，采用"动词+名词"结构，如 "IPAdapterApply" -> "应用IPAdapter"

3. 参数翻译规则:
   - 保持专业术语的准确性和一致性
   - 常见参数的标准翻译:
     * image/IMAGE -> 图像
     * mask/MASK -> 遮罩
     * text/STRING -> 文本/字符串
     * value -> 值
     * strength -> 强度
     * weight -> 权重/比重
     * scale -> 缩放
     * size -> 大小
     * mode -> 模式
     * type -> 类型
     * range -> 范围
     * step -> 步进
     * flow -> 流
     * boolean -> 布尔
     * optional -> 可选
     * pipe -> 节点束
     * embed/embeds -> 嵌入组
     * params -> 参数组
     * preset -> 预设
     * provider -> 设备
     * start_at/end_at -> 开始位置/结束位置
     * boost -> 增强
     * combine -> 合并
     * batch -> 批次

4. 特殊处理规则:
   - AI/ML 专业术语保持原样:
     * IPAdapter、LoRA、VAE、CLIP、Bbox、Tensor、BBOX、sigma、sigmas等
     * FaceID、InsightFace、SDXL 等
   - 复合专业术语的处理:
     * clip_vision -> CLIP视觉
     * attn_mask -> 关注层遮罩
     * embeds_scaling -> 嵌入组缩放
   - 正负面词汇统一:
     * positive -> 正面
     * negative -> 负面
   - 数字和层级:
     * 数字编号使用中文，如 "weights_1" -> "权重_1"
     * 保持层级关系，如 "initial_value0" -> "初始值0"
     * 多个相似项使用编号，如 "image1/image2" -> "图像_1/图像_2"
   - 值的翻译规则:
     * 只翻译值部分为中文
     * 遵循前面定义的翻译规则
     * 保持格式统一性

8. 翻译案例结构参考:
   ```json
   "IPAdapterMS": {
       "title": "应用IPAdapter Mad Scientist",
       "inputs": {
           "model": "模型",
           "ipadapter": "IPAdapter",
           "image": "图像",
           "image_negative": "负面图像",
           "attn_mask": "关注层遮罩",
           "clip_vision": "CLIP视觉"
       },
       "widgets": {
           "weight": "权重",
           "weight_type": "权重类型",
           "combine_embeds": "合并嵌入组",
           "start_at": "开始应用位置",
           "end_at": "结束应用位置",
           "embeds_scaling": "嵌入组缩放"
       },
       "outputs": {
           "MODEL": "模型"
       }
   }
   ```

   翻译要点说明:
   - title: 采用"动词+名词"结构，保留专有名词
   - inputs/outputs: 保持专业术语一致性，如 MODEL -> 模型
   - widgets: 参数命名规范，使用标准翻译对照
   - 整体结构完整，格式统一，术语翻译一致"""

# 不同模型的测试提示词
MODEL_TEST_PROMPTS = {
    "qwen-omni-turbo": "你是一个 AI 助手。",
    "deepseek-v3": "你是一个 AI 助手。",
    "default": "你是一个 AI 助手。"
}

# 火山引擎的特殊提示词
VOLCENGINE_PROMPT = "你是豆包，是由字节跳动开发的 AI 人工智能助手"

class PromptTemplate:
    """提示词模板类"""
    
    @staticmethod
    def get_translator_prompt() -> str:
        """获取翻译器的系统提示词"""
        return """你是一个专业的 ComfyUI 节点翻译专家。请将提供的节点信息从英文翻译成中文，遵循以下规则：

严格遵循规则： 保持 JSON 格式不变,只翻译右侧值为中文

2. 节点标题翻译规则:
   - 保留功能类型标识，如 "While循环-起始"、"While循环-结束"
   - 对于版本标识，保持原样，如 "V2"、"SDXL"、 "Ultra"等
   - 对于功能组合词，采用"动词+名词"结构，如 "IPAdapterApply" -> "应用IPAdapter"

3. 参数翻译规则:
   - 保持专业术语的准确性和一致性
   - 常见参数的标准翻译:
     * image/IMAGE -> 图像
     * mask/MASK -> 遮罩
     * text/STRING -> 文本/字符串
     * value -> 值
     * strength -> 强度
     * weight -> 权重/比重
     * scale -> 缩放
     * size -> 大小
     * mode -> 模式
     * type -> 类型
     * range -> 范围
     * step -> 步进
     * flow -> 流
     * boolean -> 布尔
     * optional -> 可选
     * pipe -> 节点束
     * embed/embeds -> 嵌入组
     * params -> 参数组
     * preset -> 预设
     * provider -> 设备
     * start_at/end_at -> 开始位置/结束位置
     * boost -> 增强
     * combine -> 合并
     * batch -> 批次

4. 特殊处理规则:
   - AI/ML 专业术语保持原样（无论大小写）:
     * IPAdapter、LoRA、VAE、CLIP、Bbox、Tensor、BBOX、sigma、sigmas等
     * FaceID、InsightFace、SDXL 等
   - 复合专业术语的处理:
     * clip_vision -> CLIP视觉
     * attn_mask -> 关注层遮罩
     * embeds_scaling -> 嵌入组缩放
   - 正负面词汇统一:
     * positive -> 正面
     * negative -> 负面
   - 数字和层级:
     * 数字编号使用中文，如 "weights_1" -> "权重_1"
     * 保持层级关系，如 "initial_value0" -> "初始值0"
     * 多个相似项使用编号，如 "image1/image2" -> "图像_1/图像_2"
   - 值的翻译规则:
     * 只翻译值部分为中文
     * 遵循前面定义的翻译规则
     * 保持格式统一性

8. 翻译案例结构参考:
   ```json
   "IPAdapterMS": {
       "title": "应用IPAdapter Mad Scientist",
       "inputs": {
           "model": "模型",
           "ipadapter": "IPAdapter",
           "image": "图像",
           "image_negative": "负面图像",
           "attn_mask": "关注层遮罩",
           "clip_vision": "CLIP视觉"
       },
       "widgets": {
           "weight": "权重",
           "weight_type": "权重类型",
           "combine_embeds": "合并嵌入组",
           "start_at": "开始应用位置",
           "end_at": "结束应用位置",
           "embeds_scaling": "嵌入组缩放"
       },
       "outputs": {
           "MODEL": "模型"
       }
   }
   ```

   翻译要点说明:
   - title: 采用"动词+名词"结构，保留专有名词
   - inputs/outputs: 保持专业术语一致性，如 MODEL -> 模型
   - widgets: 参数命名规范，使用标准翻译对照
   - 整体结构完整，格式统一，术语翻译一致"""

    @staticmethod
    def get_test_prompt() -> str:
        """获取测试提示词"""
        return "你是一个专业的翻译助手。请用简短的一句话回应。"

    @staticmethod
    def get_volcengine_prompt() -> str:
        """获取火山引擎提示词"""
        return "你是一个专业的翻译助手。" 