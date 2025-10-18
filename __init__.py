import os
import json
import importlib.util
import sys
import asyncio
import logging

# -------------------------------------------------------------------
# 忽略 Windows asyncio 连接重置错误
# -------------------------------------------------------------------
def ignore_asyncio_connection_errors():
    """忽略 Windows 上 asyncio 的连接重置错误"""
    try:
        # 设置 asyncio 日志级别，忽略连接重置错误
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.ERROR)
        
        # 添加自定义异常处理器
        def custom_exception_handler(loop, context):
            exception = context.get('exception')
            if exception:
                # 忽略连接重置错误
                if isinstance(exception, (ConnectionResetError, ConnectionAbortedError)):
                    return
                # 忽略特定的 Windows 错误
                if hasattr(exception, 'winerror') and exception.winerror == 10054:
                    return
            
            # 对于其他异常，使用默认处理
            loop.default_exception_handler(context)
        
        # 获取当前事件循环并设置异常处理器
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(custom_exception_handler)
        except RuntimeError:
            # 如果没有运行的事件循环，设置默认策略
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        print("[AFA] 已设置 asyncio 异常处理器，忽略连接重置错误")
        
    except Exception as e:
        print(f"[AFA] 设置 asyncio 异常处理器时出错: {e}")

# 初始化异常处理
ignore_asyncio_connection_errors()

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
        print(f"!!! [AFA] {file_description} file not found. Please create it at: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"!!! [AFA] Error loading {file_description} from {file_path}: {e}")
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
        print(f"!!! [AFA] Could not find module at {file_path}")
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

# 导入音乐模块
suno_music_generator = import_module_from_path(
    "suno_music_generator",
    os.path.join(NODE_DIR, "core", "Online-api-service", "music", "suno_music_generator.py")
)
suno_music_extender = import_module_from_path(
    "suno_music_extender",
    os.path.join(NODE_DIR, "core", "Online-api-service", "music", "suno_music_extender.py")
)
suno_music_cover = import_module_from_path(
    "suno_music_cover",
    os.path.join(NODE_DIR, "core", "Online-api-service", "music", "suno_music_cover.py")
)

# 导入飞书模块
feishu_config = import_module_from_path(
    "feishu_config",
    os.path.join(NODE_DIR, "core", "Online-api-service", "feishu", "feishu_config.py")
)
feishu_read = import_module_from_path(
    "feishu_read",
    os.path.join(NODE_DIR, "core", "Online-api-service", "feishu", "feishu_read.py")
)
feishu_write = import_module_from_path(
    "feishu_write",
    os.path.join(NODE_DIR, "core", "Online-api-service", "feishu", "feishu_write.py")
)
feishu_read_diff = import_module_from_path(
    "feishu_read_diff",
    os.path.join(NODE_DIR, "core", "Online-api-service", "feishu", "feishu_read_diff.py")
)
feishu_upload_image = import_module_from_path(
    "feishu_upload_image",
    os.path.join(NODE_DIR, "core", "Online-api-service", "feishu", "feishu_upload_image.py")
)

# 导入2D动画工具模块 - LayerEdit
create_blank_document = import_module_from_path(
    "create_blank_document",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Create_blank_document.py")
)
obtain_document_information = import_module_from_path(
    "obtain_document_information",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Obtain_document_information.py")
)
get_layer_from_document = import_module_from_path(
    "get_layer_from_document",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Get_layer_from_document.py")
)
get_layer_list_from_document = import_module_from_path(
    "get_layer_list_from_document",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Get_layer_list_from_document.py")
)
unpack_layer = import_module_from_path(
    "unpack_layer",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Unpack_layer.py")
)

update_layer = import_module_from_path(
    "update_layer",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Update_layer.py")
)
delete_layer = import_module_from_path(
    "delete_layer",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Delete_layer.py")
)
add_layer_to_document = import_module_from_path(
    "add_layer_to_document",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Add_layer_to_document.py")
)
get_layer_info = import_module_from_path(
    "get_layer_info",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Get_layer_info.py")
)
create_layer = import_module_from_path(
    "create_layer",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerEdit", "Create_layer.py")
)

# 2D动画工具节点 - LayerUtils
preview_document = import_module_from_path(
    "preview_document",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerUtils", "Preview_document.py")
)
preview_layer = import_module_from_path(
    "preview_layer",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerUtils", "Preview_layer.py")
)

# 2D动画工具节点 - LayerIO
import_psd = import_module_from_path(
    "import_psd",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerIO", "import_psd.py")
)
export_psd = import_module_from_path(
    "export_psd",
    os.path.join(NODE_DIR, "core", "2d-animation-tools", "LayerIO", "export_psd.py")
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

# 音乐模块节点
SunoMusicGeneratorNode = suno_music_generator.SunoMusicGenerator
SunoMusicExtenderNode = suno_music_extender.SunoMusicExtender
SunoMusicCoverNode = suno_music_cover.SunoMusicCover

# 飞书API节点
FeishuConfigNode = feishu_config.FeishuConfigNode
FeishuReadNode = feishu_read.FeishuReadNode
FeishuWriteNode = feishu_write.FeishuWriteNode
FeishuReadDiffNode = feishu_read_diff.FeishuReadDiffNode
FeishuUploadImageNode = feishu_upload_image.FeishuUploadImageNode

# 2D动画工具节点 - LayerEdit
CreateBlankDocumentNode = create_blank_document.CreateBlankDocumentNode
ObtainDocumentInformationNode = obtain_document_information.ObtainDocumentInformationNode
GetLayerFromDocumentNode = get_layer_from_document.GetLayerFromDocumentNode
GetLayerListFromDocumentNode = get_layer_list_from_document.GetLayerListFromDocumentNode
UnpackLayerNode = unpack_layer.UnpackLayerNode
UpdateLayerNode = update_layer.UpdateLayerNode
DeleteLayerNode = delete_layer.DeleteLayerNode
AddLayerToDocumentNode = add_layer_to_document.AddLayerToDocumentNode
GetLayerInfoNode = get_layer_info.GetLayerInfoNode
CreateLayerNode = create_layer.CreateLayerNode

# 2D动画工具节点 - LayerUtils
PreviewDocumentNode = preview_document.PreviewDocumentNode
PreviewLayerNode = preview_layer.PreviewLayerNode

# 2D动画工具节点 - LayerIO
ImportPSDNode = import_psd.ImportPSDNode
ExportPSDAdvancedNode = export_psd.ExportPSDAdvancedNode

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
    # 音乐模块
    "SunoMusicGenerator": SunoMusicGeneratorNode,
    "SunoMusicExtender": SunoMusicExtenderNode,
    "SunoMusicCover": SunoMusicCoverNode,
    # 飞书API节点
    "FeishuConfig": FeishuConfigNode,
    "FeishuRead": FeishuReadNode,
    "FeishuWrite": FeishuWriteNode,
    "FeishuReadDiff": FeishuReadDiffNode,
    "FeishuUploadImage": FeishuUploadImageNode,
    # 2D动画工具节点 - LayerEdit
    "CreateBlankDocument": CreateBlankDocumentNode,
    "ObtainDocumentInformation": ObtainDocumentInformationNode,
    "GetLayerFromDocument": GetLayerFromDocumentNode,
    "GetLayerListFromDocument": GetLayerListFromDocumentNode,
    "UnpackLayer": UnpackLayerNode,
    "UpdateLayer": UpdateLayerNode,
    "DeleteLayer": DeleteLayerNode,
    "AddLayerToDocument": AddLayerToDocumentNode,
    "GetLayerInfo": GetLayerInfoNode,
    "CreateLayer": CreateLayerNode,
    # 2D动画工具节点 - LayerUtils
    "PreviewDocument": PreviewDocumentNode,
    "PreviewLayer": PreviewLayerNode,
    # 2D动画工具节点 - LayerIO
    "ImportPSD": ImportPSDNode,
    "ExportPSDAdvanced": ExportPSDAdvancedNode,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "APIKeySelector": "API Key Selector", "BaseURLSelector": "Base URL Selector",
    "ModelNameSelector": "Model Name Selector", "SystemPromptSelector": "System Prompt Selector",
    "WorldbuildingUserInput": "用户输入: 世界观构建", "CharacterUserInput": "用户输入: 角色档案",
    "SaveTheCatUserInput": "用户输入: 救猫咪结构", "ScreenwriterUserInput": "用户输入: 剧本场景",
    "StoryboardUserInput": "用户输入: 分镜设计", "UltimateLLMPrompter": "LLM Prompter (All-in-One)",
    "UltimateVLMPrompter": "VLM Prompter (All-in-One)", "ImageEditNode": "图像生成/图像编辑",
    # 音乐模块
    "SunoMusicGenerator": "Suno音乐生成器",
    "SunoMusicExtender": "Suno音乐续写器",
    "SunoMusicCover": "Suno音乐翻唱器",
    # 飞书API节点显示名称
    "FeishuConfig": "飞书数据配置",
    "FeishuRead": "飞书读取数据",
    "FeishuWrite": "飞书写入数据",
    "FeishuReadDiff": "飞书读取数据差",
    "FeishuUploadImage": "飞书上传图像",
    # 2D动画工具节点显示名称 - LayerEdit
    "CreateBlankDocument": "创建空白文档",
    "ObtainDocumentInformation": "获取文档信息",
    "GetLayerFromDocument": "从文档获取图层",
    "GetLayerListFromDocument": "从文档获取图层列表",
    "UnpackLayer": "解包图层",
    "UpdateLayer": "更新图层",
    "DeleteLayer": "删除图层",
    "AddLayerToDocument": "添加图层到文档",
    "GetLayerInfo": "获取图层信息",
    "CreateLayer": "创建图层",
    # 2D动画工具节点显示名称 - LayerUtils
    "PreviewDocument": "预览文档",
    "PreviewLayer": "预览图层",
    # 2D动画工具节点 - LayerIO
    "ImportPSD": "导入PSD文档",
    "ExportPSDAdvanced": "导出PSD文档",
}

# 导出JavaScript文件目录，使前端扩展能被加载
WEB_DIRECTORY = "./js"

# 导出所有必要的变量
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]