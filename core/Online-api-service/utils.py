import os
import json
import time
import torch
import numpy as np
from PIL import Image
import io
import base64
import requests
import sys

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.abspath(os.path.join(current_dir, "../.."))
# 将项目根目录添加到sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)

# 从主模块导入配置数据
sys.path.insert(0, root_dir)
import __init__ as main_module
CONFIG_DATA = main_module.CONFIG_DATA
SYSTEM_PROMPTS_DATA = main_module.SYSTEM_PROMPTS_DATA
USER_PROMPTS_DATA = main_module.USER_PROMPTS_DATA

# -------------------------------------------------------------------
# 通用选择器节点基类
# -------------------------------------------------------------------
class GenericSelectorNode:
    _data_source = None; _config_key = None
    @classmethod
    def INPUT_TYPES(cls):
        if cls._data_source is None: raise NotImplementedError("Subclass must define a _data_source.")
        items = cls._data_source.get(cls._config_key, {}) if cls._config_key else cls._data_source
        display_names = list(items.keys()) or [f"(Empty) Please check your config file"]
        return {"required": {"display_name": (display_names,)}}
    FUNCTION = "select_value"
    def select_value(self, display_name):
        items = self._data_source.get(self._config_key, {}) if self._config_key else self._data_source
        value = items.get(display_name, "")
        if not value:
            source_name = self._config_key or "the config file"
            print(f"!!! [Magic Nodes] Could not find value for '{display_name}' in '{source_name}'")
        return (value,)

# -------------------------------------------------------------------
# 用户提示模板格式化函数
# -------------------------------------------------------------------
def format_user_prompt(template_key, **kwargs):
    template = USER_PROMPTS_DATA.get(template_key)
    if not template: return (f"Error: User prompt template '{template_key}' not found.",)
    try:
        return (template.format(**kwargs),)
    except KeyError as e:
        return (f"Error: Missing placeholder {e} for user prompt template '{template_key}'.",)

# -------------------------------------------------------------------
# 图像处理工具函数
# -------------------------------------------------------------------
def tensor_to_bytes(image_tensor):
    img = image_tensor[0]; i = 255. * img.cpu().numpy(); img_np = np.clip(i, 0, 255).astype(np.uint8)
    pil_image = Image.fromarray(img_np); buffer = io.BytesIO(); pil_image.save(buffer, format="JPEG")
    return buffer.getvalue()

def url_to_tensor(url):
    response = requests.get(url, timeout=20); response.raise_for_status()
    img_bytes = response.content; pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_np = np.array(pil_image, dtype=np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)

def encode_image_to_base64(image_tensor):
    img = image_tensor[0]; i = 255. * img.cpu().numpy(); img_np = np.clip(i, 0, 255).astype(np.uint8)
    pil_image = Image.fromarray(img_np); buffer = io.BytesIO(); pil_image.save(buffer, format="JPEG")
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}" 