"""翻译服务配置"""

class TranslationServiceConfig:
    """翻译服务基础配置类"""
    def __init__(self):
        self.name = ""
        self.models = []
        self.enabled = True
        self.requires_model_id = False
        self.default_model = ""

class AliyunConfig(TranslationServiceConfig):
    """阿里云翻译服务配置"""
    def __init__(self):
        super().__init__()
        self.name = "aliyun"
        self.models = [
            "qwen-turbo",
            "qwen-plus", 
            "qwen-max",
            "qwen-max-longcontext"
        ]
        self.enabled = True
        self.default_model = "qwen-plus"

class VolcengineConfig(TranslationServiceConfig):
    """火山引擎翻译服务配置"""
    def __init__(self):
        super().__init__()
        self.name = "volcengine"
        self.models = []  # 不提供预设模型列表
        self.enabled = True  # 启用服务
        self.requires_model_id = True  # 需要手动输入模型ID
        self.default_model = ""  # 无默认模型
        self.model_selection_enabled = False  # 禁用模型选择

class TranslationServices:
    """翻译服务管理器"""
    def __init__(self):
        self.services = {
            "aliyun": AliyunConfig(),
            "volcengine": VolcengineConfig()
        }
    
    def get_service(self, name: str) -> TranslationServiceConfig:
        """获取指定服务的配置"""
        return self.services.get(name)
    
    def get_enabled_services(self) -> list:
        """获取所有启用的服务"""
        return [s for s in self.services.values() if s.enabled]

class TranslationConfig:
    """翻译配置类"""
    
    # 需要保持原样的大写类型值
    PRESERVED_TYPES = {
        'IMAGE', 'MASK', 'MODEL', 'CROP_DATA', 'ZIP', 'PDF', 'CSV',
        'INT', 'FLOAT', 'BOOLEAN', 'STRING', 'BBOX_LIST'
    }
    
    # 需要保持原样的技术参数键名
    PRESERVED_KEYS = {
        'width', 'height', 'width_old', 'height_old', 'job_id', 'user_id',
        'base64_string', 'image_quality', 'image_format'
    }
    
    # 通用参数翻译映射
    COMMON_TRANSLATIONS = {
        'image': '图像',
        'mask': '遮罩',
        'model': '模型',
        'processor': '处理器',
        'device': '设备',
        'bbox': '边界框',
        'samples': '样本',
        'operation': '操作',
        'guide': '引导图',
        'source': '源',
        'destination': '目标',
        'threshold': '阈值',
        'radius': '半径',
        'epsilon': 'epsilon',
        'contrast': '对比度',
        'brightness': '亮度',
        'saturation': '饱和度',
        'hue': '色调',
        'gamma': '伽马值',
        'index': '索引',
        'position': '位置',
        'size': '大小',
        'scale': '缩放',
        'dilation': '膨胀',
        'count': '计数',
        'result': '结果'
    }
    
    # 人体部位翻译映射
    BODY_PART_TRANSLATIONS = {
        'background': '背景',
        'skin': '皮肤',
        'nose': '鼻子',
        'eye': '眼睛',
        'eye_g': '眼镜',
        'brow': '眉毛',
        'ear': '耳朵',
        'mouth': '嘴巴',
        'lip': '嘴唇',
        'hair': '头发',
        'hat': '帽子',
        'neck': '脖子',
        'cloth': '衣服'
    }
    
    # 方向和位置翻译映射
    DIRECTION_TRANSLATIONS = {
        # 前缀
        'l_': '左',
        'r_': '右',
        'u_': '上',
        'b_': '下',
        # 后缀
        '_l': '左',
        '_r': '右',
        '_t': '上',
        '_b': '下'
    }
    
    @classmethod
    def get_translation(cls, text: str) -> str:
        """获取文本的翻译
        
        Args:
            text: 要翻译的文本
            
        Returns:
            str: 翻译后的文本，如果没有找到翻译则返回原文
        """
        # 1. 检查是否是保留类型
        if text.upper() in cls.PRESERVED_TYPES:
            return text
            
        # 2. 检查是否在通用翻译中
        if text.lower() in cls.COMMON_TRANSLATIONS:
            return cls.COMMON_TRANSLATIONS[text.lower()]
            
        # 3. 检查是否是人体部位
        if text in cls.BODY_PART_TRANSLATIONS:
            return cls.BODY_PART_TRANSLATIONS[text]
            
        # 4. 检查是否包含方向前缀/后缀
        for prefix, direction in cls.DIRECTION_TRANSLATIONS.items():
            if text.startswith(prefix) or text.endswith(prefix):
                base = text.replace(prefix, '')
                if base in cls.BODY_PART_TRANSLATIONS:
                    return f"{direction}{cls.BODY_PART_TRANSLATIONS[base]}"
                    
        return text
    
    @classmethod
    def should_preserve_key(cls, key: str) -> bool:
        """检查是否应该保持键名不变
        
        Args:
            key: 键名
            
        Returns:
            bool: 是否应该保持不变
        """
        return key.lower() in cls.PRESERVED_KEYS 