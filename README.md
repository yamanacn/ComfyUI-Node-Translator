# ComfyUI 节点翻译工具

一个用于翻译 ComfyUI 插件节点信息的工具，支持批量检测和翻译节点信息。

## 功能特点

- 自动检测插件目录中的节点信息
- 使用火山引擎 API 进行中文翻译
- 支持批量翻译和进度显示
- 提供节点对比功能
- 详细的翻译日志和费用统计

## API 配置说明

### 火山引擎 API 配置
1. 访问[火山引擎控制台](https://console.volcengine.com/)
2. 创建 API 密钥，获取 `API Key`
3. 创建翻译模型，获取 `Model ID`
4. 在程序中填入 API 密钥和模型 ID
5. 点击"测试 API"确认连接正常

### 费率说明
- 输入 tokens：0.0008元/千tokens
- 输出 tokens：0.0020元/千tokens
- 程序会自动计算并显示预估费用

## 使用说明

### 快速开始
1. 运行 `run.bat` 启动程序
2. 在主界面填入 API 密钥和模型 ID
3. 点击"保存配置"保存 API 信息
4. 点击"测试 API"验证连接

### 翻译功能
1. 点击"选择文件夹"选择要翻译的插件目录
2. 点击"检测节点"扫描插件中的节点
3. 可以点击"查看待翻译 JSON"查看检测到的节点
4. 设置批次大小（建议：5-8）
5. 点击"开始翻译"开始翻译过程
6. 翻译完成后可点击"查看结果"查看翻译结果

### 对比功能
1. 切换到"对比功能"标签页
2. 选择旧版本节点文件
3. 选择新版本节点文件
4. 点击"比较节点"进行对比
5. 可以点击"打开结果文件"查看详细对比结果

## 功能说明

### 主要功能
- **节点检测**：扫描插件目录，识别所有 ComfyUI 节点
- **节点翻译**：将节点信息翻译成中文
- **节点对比**：对比两个版本的节点差异
- **结果查看**：支持查看待翻译内容和翻译结果

### 辅助功能
- **API 测试**：验证 API 连接是否正常
- **配置保存**：保存 API 密钥和模型 ID
- **进度显示**：显示翻译进度和详细日志
- **费用统计**：统计 tokens 使用量和预估费用

### 输出文件
所有文件都保存在程序目录下的 `output/插件名/` 文件夹中：
- `temp/`: 临时文件目录
- `translations/`: 翻译结果目录
- `logs/`: 日志文件目录
- `debug/`: 调试信息目录

## 注意事项

1. 确保有稳定的网络连接
2. API 密钥请妥善保管，不要泄露
3. 建议先用小批量测试翻译效果
4. 如遇到问题，查看日志获取详细信息
5. 翻译费用以实际计费为准

## 更新日志

### v1.0.0
- 初始版本发布
- 支持火山引擎翻译服务
- 实现基本的节点检测和翻译功能
- 添加节点对比功能

## 开发说明

### GitHub 仓库设置
1. 在 GitHub 创建新仓库 `ComfyUI-Node-Translator`
2. 设置仓库为公开，添加 README、.gitignore (Python)、LICENSE

### 本地仓库设置
```bash
# 初始化 Git 仓库
git init

# 添加远程仓库
git remote add origin https://github.com/你的用户名/ComfyUI-Node-Translator.git

# 添加文件到暂存区
git add .

# 创建首次提交
git commit -m "Initial commit: ComfyUI 节点翻译工具"

# 推送到 GitHub
git push -u origin main
```

### 目录结构
```
ComfyUI-Node-Translator/
├── README.md           # 项目说明文档
├── requirements.txt    # 项目依赖
├── run.bat            # 启动脚本
├── main.py            # 主程序
├── config.template.json # 配置模板
└── src/               # 源代码目录
    ├── __init__.py
    ├── node_parser.py   # 节点解析模块
    ├── translator.py    # 翻译服务模块
    ├── file_utils.py    # 文件处理工具
    ├── prompts.py       # 提示词模板
    ├── translation_config.py  # 翻译配置
    ├── node_diff.py     # 节点对比模块
    └── diff_tab.py      # 对比功能界面
``` 