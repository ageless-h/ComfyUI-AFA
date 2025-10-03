import requests
import sys
import os

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 导入工具类
utils_path = os.path.join(current_dir, "..", "utils.py")
import importlib.util
spec = importlib.util.spec_from_file_location("utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
tensor_to_bytes = utils.tensor_to_bytes
url_to_tensor = utils.url_to_tensor

# -------------------------------------------------------------------
# 图像编辑 (Image Edit) 节点
# -------------------------------------------------------------------
class ImageEditNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"api_key":("API_KEY",), "base_url":("BASE_URL",), "模型": ("MODEL_NAME",), "图像":("IMAGE",), "编辑指令":("STRING", {"multiline": True}), "返回格式":(["url", "b64_json"],),}}
    RETURN_TYPES = ("IMAGE", "STRING",); RETURN_NAMES = ("图像", "图片URL",); FUNCTION = "edit_image"; CATEGORY = "AFA/图像"
    def edit_image(self, api_key, base_url, 模型, 图像, 编辑指令, 返回格式):
        if not all([api_key, base_url, 图像 is not None, 编辑指令]): return (None, "Error: Missing required inputs.")
        endpoint_url = base_url.rstrip('/') + "/v1/images/edits"
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {"model": 模型, "prompt": 编辑指令, "response_format": 返回格式}
        try:
            image_bytes = tensor_to_bytes(图像)
            files = {'image': ('input_image.jpg', image_bytes, 'image/jpeg')}
        except Exception as e: return (None, f"Error converting input image: {e}")
        try:
            print(f"[Image Edit] Calling API: {endpoint_url} with model: {模型}"); response = requests.post(endpoint_url, headers=headers, data=data, files=files, timeout=120)
            response.raise_for_status(); response_data = response.json()
            image_url = response_data.get("data", [{}])[0].get("url")
            if not image_url: return (None, f"Error: Image URL not found in API response: {response_data}")
            print(f"[Image Edit] Successfully got image URL: {image_url}"); output_image_tensor = url_to_tensor(image_url)
            return (output_image_tensor, image_url)
        except requests.exceptions.RequestException as e: return (None, f"API request failed: {e}")
        except Exception as e: return (None, f"An unexpected error occurred: {e}") 