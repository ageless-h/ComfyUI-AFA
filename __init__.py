import os
import json
import importlib.util
import sys

# -------------------------------------------------------------------
# 配置加载器
# -------------------------------------------------------------------
NODE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(NODE_DIR, "config", "config.json")
SYSTEM_PROMPTS_PATH = os.path.join(NODE_DIR, "config", "system_prompts.json")
USER_PROMPTS_PATH = os.path.join(NODE_DIR, "config", "user_prompts.json")

def load_json_config(file_path, file_description):
    """一个通用的JSON文件加载函数，带有清晰的错误提示"""
    if not os.path.exists(file_path):
        print(f"!!! [Magic Nodes] {file_description} file not found. Please create it at: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"!!! [Magic Nodes] Error loading {file_description} from {file_path}: {e}")
        return {}

CONFIG_DATA = load_json_config(CONFIG_PATH, "Core Config")
SYSTEM_PROMPTS_DATA = load_json_config(SYSTEM_PROMPTS_PATH, "System Prompts")
USER_PROMPTS_DATA = load_json_config(USER_PROMPTS_PATH, "User Prompt Templates")

# -------------------------------------------------------------------
# 动态导入模块
# -------------------------------------------------------------------
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        print(f"!!! [Magic Nodes] Could not find module at {file_path}")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 导入选择器模块
api_selectors = import_module_from_path(
    "api_selectors", 
    os.path.join(NODE_DIR, "core", "Online-api-service", "Selector", "api_selectors.py")
)
user_inputs = import_module_from_path(
    "user_inputs", 
    os.path.join(NODE_DIR, "core", "Online-api-service", "Selector", "user_inputs.py")
)

# 导入LLM模块
llm_prompter = import_module_from_path(
    "llm_prompter", 
    os.path.join(NODE_DIR, "core", "Online-api-service", "Large-language-model", "llm_prompter.py")
)

# 导入VLM模块
vlm_prompter = import_module_from_path(
    "vlm_prompter", 
    os.path.join(NODE_DIR, "core", "Online-api-service", "Visual-language-model", "vlm_prompter.py")
)

# 导入图像编辑模块
image_edit = import_module_from_path(
    "image_edit", 
    os.path.join(NODE_DIR, "core", "Online-api-service", "image-edit", "image_edit.py")
)

# 从模块中获取类
APIKeySelectorNode = api_selectors.APIKeySelectorNode
BaseURLSelectorNode = api_selectors.BaseURLSelectorNode
ModelNameSelectorNode = api_selectors.ModelNameSelectorNode
SystemPromptSelectorNode = api_selectors.SystemPromptSelectorNode

WorldbuildingUserInputNode = user_inputs.WorldbuildingUserInputNode
CharacterUserInputNode = user_inputs.CharacterUserInputNode
SaveTheCatUserInputNode = user_inputs.SaveTheCatUserInputNode
ScreenwriterUserInputNode = user_inputs.ScreenwriterUserInputNode
StoryboardUserInputNode = user_inputs.StoryboardUserInputNode

UltimateLLMPrompterNode = llm_prompter.UltimateLLMPrompterNode
UltimateVLMPrompterNode = vlm_prompter.UltimateVLMPrompterNode
ImageEditNode = image_edit.ImageEditNode

# -------------------------------------------------------------------
# 注册所有节点到 ComfyUI
# -------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "APIKeySelector": APIKeySelectorNode, "BaseURLSelector": BaseURLSelectorNode,
    "ModelNameSelector": ModelNameSelectorNode, "SystemPromptSelector": SystemPromptSelectorNode,
    "WorldbuildingUserInput": WorldbuildingUserInputNode, "CharacterUserInput": CharacterUserInputNode,
    "SaveTheCatUserInput": SaveTheCatUserInputNode, "ScreenwriterUserInput": ScreenwriterUserInputNode,
    "StoryboardUserInput": StoryboardUserInputNode, "UltimateLLMPrompter": UltimateLLMPrompterNode,
    "UltimateVLMPrompter": UltimateVLMPrompterNode, "ImageEditNode": ImageEditNode,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "APIKeySelector": "API Key Selector", "BaseURLSelector": "Base URL Selector",
    "ModelNameSelector": "Model Name Selector", "SystemPromptSelector": "System Prompt Selector",
    "WorldbuildingUserInput": "用户输入: 世界观构建", "CharacterUserInput": "用户输入: 角色档案",
    "SaveTheCatUserInput": "用户输入: 救猫咪结构", "ScreenwriterUserInput": "用户输入: 剧本场景",
    "StoryboardUserInput": "用户输入: 分镜设计", "UltimateLLMPrompter": "LLM Prompter (All-in-One)",
    "UltimateVLMPrompter": "VLM Prompter (All-in-One)", "ImageEditNode": "图像编辑 (Nano-banana)",
}