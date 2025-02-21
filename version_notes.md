# ComfyUI 节点翻译工具 - 版本记录

## V1.0.0 (当前版本)

### 核心功能
1. 节点检测
   - 自动扫描插件目录
   - 识别 ComfyUI 节点结构
   - 生成待翻译 JSON 文件

2. 翻译功能
   - 使用火山引擎 API
   - 批量翻译支持
   - 进度显示和日志记录
   - tokens 使用统计
   - 费用预估

3. 对比功能
   - 新旧版本节点对比
   - 差异节点识别
   - 结果文件生成

### 技术特性
1. 文件管理
   - 输出目录结构化
   - 临时文件自动清理
   - 虚拟环境支持

2. 错误处理
   - API 错误识别
   - 翻译失败重试
   - 详细错误日志

3. 配置管理
   - API 密钥保存
   - 模型 ID 配置
   - 国内源支持

### 文件结构
```
ComfyUI-Node-Translator/
├── README.md
├── requirements.txt
├── run.bat
├── run(国内源).bat
├── src/
│   ├── __init__.py
│   ├── node_parser.py
│   ├── translator.py
│   ├── file_utils.py
│   ├── prompts.py
│   ├── translation_config.py
│   ├── node_diff.py
│   └── diff_tab.py
└── main.py
```

### 依赖版本
- flask==3.0.2
- openai==1.12.0
- requests==2.31.0

### 已知问题
1. 需要配合 AIGODLIKE-ComfyUI-Translation 使用
2. 翻译结果需要手动复制到目标目录

### 发布日期
2024-02-20 