# ComfyUI-AFA (AI For Animation)

ComfyUI-AFA是一个为动画创作者设计的ComfyUI扩展节点集合，提供了一系列强大的AI辅助工具，帮助创作者更高效地完成动画创作流程。

## 功能特点

- **多种API服务集成**：支持多种在线API服务，包括硅基流动、t8等
- **LLM文本生成**：集成大语言模型，用于剧本、角色设定、世界观构建等创作任务
- **VLM视觉分析**：集成视觉语言模型，用于图像分析和描述
- **图像编辑**：支持基于文本提示的图像编辑功能
- **音乐生成**：支持基于文本描述生成音乐，可控制时长和风格
- **结构化创作流程**：提供世界观构建、角色档案、救猫咪结构等专业创作模板
- **统一界面**：所有节点采用统一的AFA分类，便于查找和使用

## 安装方法

### 方法1：通过ComfyUI Manager安装

1. 在ComfyUI中安装[ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager)
2. 打开ComfyUI，点击"Manager"标签
3. 在搜索框中输入"ComfyUI-AFA"并安装

### 方法2：手动安装

```bash
cd /path/to/ComfyUI/custom_nodes/
git clone https://github.com/ageless-h/ComfyUI-AFA.git
```

## 配置设置

首次使用前，需要在`config`文件夹中创建以下配置文件：

1. `config.json`：API密钥、基础URL和模型名称配置
2. `system_prompts.json`：系统提示词模板
3. `user_prompts.json`：用户提示词模板

### 配置文件示例

#### config.json
```json
{
  "api_keys": {
    "服务商名称1": "你的API密钥1",
    "服务商名称2": "你的API密钥2"
  },
  "base_urls": {
    "服务商名称1": "https://api.example1.com/",
    "服务商名称2": "https://api.example2.com/"
  },
  "model_names": {
    "模型别名1": "模型实际名称1",
    "模型别名2": "模型实际名称2"
  }
}
```

#### system_prompts.json
```json
{
  "提示词名称1": "系统提示词内容1",
  "提示词名称2": "系统提示词内容2"
}
```

#### user_prompts.json
```json
{
  "模板名称1": "模板内容1 {参数1} {参数2}",
  "模板名称2": "模板内容2 {参数A} {参数B}"
}
```

## 节点说明

### 配置节点
- **API Key Selector**：选择API密钥
- **Base URL Selector**：选择API基础URL
- **Model Name Selector**：选择模型名称
- **System Prompt Selector**：选择系统提示词

### 用户输入节点
- **用户输入: 世界观构建**：用于创建动画项目的世界观设定
- **用户输入: 角色档案**：用于创建角色档案和设定
- **用户输入: 救猫咪结构**：用于构建故事大纲和结构
- **用户输入: 剧本场景**：用于编写剧本场景
- **用户输入: 分镜设计**：用于设计分镜

### AI服务节点
- **LLM Prompter (All-in-One)**：大语言模型文本生成
- **VLM Prompter (All-in-One)**：视觉语言模型图像分析
- **图像编辑 (Nano-banana)**：基于文本提示的图像编辑
- **Suno音乐生成器**：基于文本描述生成音乐

## 使用示例

### 世界观构建工作流
1. 使用**API Key Selector**、**Base URL Selector**和**Model Name Selector**配置API
2. 使用**System Prompt Selector**选择"世界观构建大师"系统提示词
3. 使用**用户输入: 世界观构建**输入项目名称、动画类型等信息
4. 连接到**LLM Prompter**节点生成世界观设定

### 图像编辑工作流
1. 使用**API Key Selector**、**Base URL Selector**和**Model Name Selector**配置API
2. 使用**LoadImage**节点加载需要编辑的图像
3. 使用**图像编辑**节点，输入编辑指令
4. 连接到**PreviewImage**节点查看结果

### 音乐生成工作流
1. 使用**API Key Selector**选择"t8"
2. 使用**Base URL Selector**选择"t8"
3. 使用**Model Name Selector**选择"t8-suno-music"
4. 使用**Suno音乐生成器**节点，输入歌曲标题、描述和标签
5. 设置最大音频时长（10-180秒）
6. 连接到**PreviewAudio**节点播放生成的音乐

## 许可证

MIT License

## 更新日志

### v1.1.0 (2025-10-03)
- **新增功能**：
  - 添加Suno音乐生成器节点，支持文本生成音乐
  - 添加音频时长控制参数，可设置10-180秒范围
  - 添加音乐标签系统，支持多个标签组合

- **改进**：
  - 优化音频格式，使用3D张量格式`[batch, channels, samples]`
  - 修复与ComfyUI官方PreviewAudio节点的兼容性问题
  - 改进API响应处理，支持t8平台的Suno API格式

- **重构**：
  - 重新组织节点分类，将所有节点迁移到AFA命名空间下
  - 将LLM/VLM节点移至`AFA/大模型`分类
  - 将配置选择器节点移至`AFA/config`分类
  - 将用户输入节点移至`AFA/输入`分类
  - 将图像编辑节点移至`AFA/图像`分类
  - 将音乐生成节点放在`AFA/音乐`分类

### v1.0.0 (2025-09-15)
- 首次发布
- 支持LLM文本生成
- 支持VLM图像分析
- 支持图像编辑
- 提供创作辅助模板

## 联系方式

如有问题或建议，请在GitHub上提交Issue或Pull Request。 