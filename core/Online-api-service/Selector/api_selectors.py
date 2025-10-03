import sys
import os

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
# 将项目根目录添加到sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)

# 导入工具类
utils_path = os.path.join(current_dir, "..", "utils.py")
import importlib.util
spec = importlib.util.spec_from_file_location("utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
GenericSelectorNode = utils.GenericSelectorNode

# 从utils模块导入配置数据
CONFIG_DATA = utils.CONFIG_DATA
SYSTEM_PROMPTS_DATA = utils.SYSTEM_PROMPTS_DATA

# -------------------------------------------------------------------
# 专用选择器节点
# -------------------------------------------------------------------
class APIKeySelectorNode(GenericSelectorNode):
    _data_source = CONFIG_DATA; _config_key = "api_keys"; RETURN_TYPES = ("API_KEY",); RETURN_NAMES = ("api_key",); CATEGORY = "AFA/config"

class BaseURLSelectorNode(GenericSelectorNode):
    _data_source = CONFIG_DATA; _config_key = "base_urls"; RETURN_TYPES = ("BASE_URL",); RETURN_NAMES = ("base_url",); CATEGORY = "AFA/config"

class ModelNameSelectorNode(GenericSelectorNode):
    _data_source = CONFIG_DATA; _config_key = "model_names"; RETURN_TYPES = ("MODEL_NAME",); RETURN_NAMES = ("model_name",); CATEGORY = "AFA/config"

class SystemPromptSelectorNode(GenericSelectorNode):
    _data_source = SYSTEM_PROMPTS_DATA; _config_key = None; RETURN_TYPES = ("STRING",); RETURN_NAMES = ("system_prompt",); CATEGORY = "AFA/config" 