import requests
import sys
import os
import base64

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
# 图像生成/编辑 (Image Generation/Edit) 节点
# -------------------------------------------------------------------
class ImageEditNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("API_KEY",),
                "base_url": ("BASE_URL",),
                "模型": ("MODEL_NAME",),
                "提示词": ("STRING", {"multiline": True}),
            },
            "optional": {
                "负面提示词": ("STRING", {"multiline": True, "default": ""}),
                "图像": ("IMAGE",),
                "图像2": ("IMAGE",),
                "图像3": ("IMAGE",),
                "图像尺寸": (["1920x1080", "1280x720", "1024x1024", "768x768", "512x512",
                           "1024x768", "768x1024", "1152x896", "896x1152", "1216x832", 
                           "832x1216", "1344x768", "768x1344", "1536x640", "640x1536"], {"default": "1024x1024"}),
                "批次大小": ("INT", {"default": 1, "min": 1, "max": 4}),
                "随机种子": ("INT", {"default": -1, "min": -1, "max": 9999999999}),
                "推理步数": ("INT", {"default": 20, "min": 1, "max": 100}),
                "引导强度": ("FLOAT", {"default": 7.5, "min": 0.0, "max": 20.0, "step": 0.1}),
                "CFG": ("FLOAT", {"default": 4.0, "min": 0.1, "max": 20.0, "step": 0.1}),
                "返回格式": (["url", "b64_json"], {"default": "url"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("图像", "图片URL", "使用的种子")
    FUNCTION = "generate_image"
    CATEGORY = "AFA/图像生成"
    
    def generate_image(self, api_key, base_url, 模型, 提示词, **kwargs):
        # 检查必需参数
        if not all([api_key, base_url, 提示词]):
            return (None, "Error: Missing required inputs.", -1)
        
        # 根据服务商与是否为编辑场景选择API端点
        is_t8 = "t8star.cn" in base_url
        has_image_input = any(kwargs.get(k) is not None for k in ["图像", "图像2", "图像3"]) 
        is_edit_model = ("Edit" in 模型) or ("Qwen-Image-Edit" in 模型)
        use_edits_endpoint = (not is_t8) and (has_image_input or is_edit_model)

        if use_edits_endpoint:
            # 非t8平台在编辑/修复场景使用edits端点
            endpoint_url = base_url.rstrip('/') + "/v1/images/edits"
        else:
            # t8平台或纯生成场景使用generations端点
            endpoint_url = base_url.rstrip('/') + "/v1/images/generations"
            
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # 构建请求数据
        data = {
            "model": 模型,
            "prompt": 提示词
        }
        
        # 根据服务商调整参数
        # is_t8 已在上方定义
        
        # 添加可选参数
        if kwargs.get("负面提示词"):
            data["negative_prompt"] = kwargs["负面提示词"]
        
        # 图像尺寸处理
        if kwargs.get("图像尺寸"):
            if is_t8:
                # t8模型使用size参数
                data["size"] = kwargs["图像尺寸"]
            elif not any(edit_model in 模型 for edit_model in ["Qwen-Image-Edit-2509", "Qwen-Image-Edit"]):
                # 硅基流动的非编辑模型使用image_size
                data["image_size"] = kwargs["图像尺寸"]
        
        # 批次大小 - 仅对Kolors模型有效
        if "Kolors" in 模型 and kwargs.get("批次大小", 1) > 1:
            data["batch_size"] = kwargs["批次大小"]
        elif is_t8 and kwargs.get("批次大小", 1) > 1:
            # t8模型使用n参数
            data["n"] = kwargs["批次大小"]
        
        # 随机种子
        if kwargs.get("随机种子", -1) >= 0:
            data["seed"] = kwargs["随机种子"]
        
        # 推理步数
        if kwargs.get("推理步数", 20) != 20:
            data["num_inference_steps"] = kwargs["推理步数"]
        
        # 引导强度 - 仅对Kolors模型有效
        if "Kolors" in 模型 and kwargs.get("引导强度", 7.5) != 7.5:
            data["guidance_scale"] = kwargs["引导强度"]
        
        # CFG - 仅对Qwen-Image模型有效
        if "Qwen-Image" in 模型 and not "Edit" in 模型 and kwargs.get("CFG", 4.0) != 4.0:
            data["cfg"] = kwargs["CFG"]
        
        # 返回格式
        if kwargs.get("返回格式", "url") == "b64_json":
            data["response_format"] = "b64_json"
        
        # 处理图像输入（仅在编辑端点或t8平台下传递图像）
        try:
            if is_t8 or use_edits_endpoint:
                # 主图像
                if kwargs.get("图像") is not None:
                    image_bytes = tensor_to_bytes(kwargs["图像"])
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    data["image"] = f"data:image/png;base64,{image_b64}"
                
                # 第二张图像 - 仅对Qwen-Image-Edit-2509有效
                if "Qwen-Image-Edit-2509" in 模型 and kwargs.get("图像2") is not None:
                    image2_bytes = tensor_to_bytes(kwargs["图像2"])
                    image2_b64 = base64.b64encode(image2_bytes).decode('utf-8')
                    data["image2"] = f"data:image/png;base64,{image2_b64}"
                
                # 第三张图像 - 仅对Qwen-Image-Edit-2509有效
                if "Qwen-Image-Edit-2509" in 模型 and kwargs.get("图像3") is not None:
                    image3_bytes = tensor_to_bytes(kwargs["图像3"])
                    image3_b64 = base64.b64encode(image3_bytes).decode('utf-8')
                    data["image3"] = f"data:image/png;base64,{image3_b64}"
        except Exception as e:
            return (None, f"Error converting input image: {e}", -1)
        
        # 发送API请求
        try:
            print(f"[Image Generation] Calling API: {endpoint_url} with model: {模型}")
            print(f"[Image Generation] Request data keys: {list(data.keys())}")
            
            response = requests.post(endpoint_url, headers=headers, json=data, timeout=120)
            print(f"[Image Generation] Response status code: {response.status_code}")
            
            # 非200时直接返回错误，避免None导致保存节点崩溃
            if response.status_code != 200:
                try:
                    err_text = response.text
                except Exception:
                    err_text = "Unknown error"
                return (None, f"API Error: status {response.status_code}, response: {err_text}", -1)

            response_data = response.json()
            print(f"[Image Generation] Response data keys: {list(response_data.keys())}")
            print(f"[Image Generation] Full response: {response_data}")
            
            # 解析响应
            images_data = None
            used_seed = response_data.get("seed", -1)
            
            # 处理不同的响应格式
            if "images" in response_data and len(response_data["images"]) > 0:
                images_data = response_data["images"]
                print(f"[Image Generation] Found images data with {len(images_data)} items")
            elif "data" in response_data and len(response_data["data"]) > 0:
                # t8可能使用data字段
                images_data = response_data["data"]
                print(f"[Image Generation] Found data field with {len(images_data)} items")
            else:
                print(f"[Image Generation] No images or data field found in response")
            
            if images_data and len(images_data) > 0:
                image_data = images_data[0]
                print(f"[Image Generation] Processing image data: {image_data}")
                
                if kwargs.get("返回格式", "url") == "b64_json":
                    # 处理base64格式
                    image_b64 = None
                    if "b64_json" in image_data:
                        image_b64 = image_data["b64_json"]
                    elif "image" in image_data:
                        # t8可能直接返回base64字符串
                        image_b64 = image_data["image"]
                    elif isinstance(image_data, str):
                        # t8可能直接返回base64字符串作为数组元素
                        image_b64 = image_data
                    
                    print(f"[Image Generation] Extracted base64 data: {image_b64 is not None}")
                    
                    if image_b64:
                        # 转换为tensor
                        import io
                        from PIL import Image
                        import torch
                        import numpy as np
                        
                        # 处理可能包含data:image前缀的base64
                        if image_b64.startswith('data:image'):
                            image_b64 = image_b64.split(',')[1]
                        
                        image_bytes = base64.b64decode(image_b64)
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        image_array = np.array(pil_image).astype(np.float32) / 255.0
                        if len(image_array.shape) == 3:
                            image_tensor = torch.from_numpy(image_array).unsqueeze(0)
                        else:
                            image_tensor = torch.from_numpy(image_array)
                        
                        return (image_tensor, "base64_image", used_seed)
                else:
                    # 处理URL格式
                    image_url = None
                    if "url" in image_data:
                        image_url = image_data["url"]
                    elif "image_url" in image_data:
                        # 某些API可能使用image_url字段
                        image_url = image_data["image_url"]
                    elif isinstance(image_data, str) and (image_data.startswith('http') or image_data.startswith('data:')):
                        # t8可能直接返回URL字符串作为数组元素
                        image_url = image_data
                    
                    print(f"[Image Generation] Extracted URL: {image_url}")
                    
                    if image_url:
                        print(f"[Image Generation] Successfully got image URL: {image_url}")
                        try:
                            output_image_tensor = url_to_tensor(image_url)
                            return (output_image_tensor, image_url, used_seed)
                        except Exception as e:
                            return (None, f"Error loading image from URL {image_url}: {e}", -1)
            
            # 如果没有找到图像数据，尝试其他可能的字段
            print(f"[Image Generation] No standard image data found, checking alternative fields...")
            
            # 检查是否有错误信息
            if "error" in response_data:
                return (None, f"API Error: {response_data['error']}", -1)
            
            # 尝试直接从响应中提取图像数据
            for key in ["image", "result", "output", "generated_image"]:
                if key in response_data:
                    potential_image = response_data[key]
                    print(f"[Image Generation] Found potential image data in '{key}' field: {type(potential_image)}")
                    
                    if isinstance(potential_image, str):
                        if potential_image.startswith('http') or potential_image.startswith('data:'):
                            # 这是一个URL或base64数据
                            if potential_image.startswith('http'):
                                try:
                                    output_image_tensor = url_to_tensor(potential_image)
                                    return (output_image_tensor, potential_image, used_seed)
                                except Exception as e:
                                    print(f"[Image Generation] Failed to load image from URL {potential_image}: {e}")
                            else:
                                # 这是base64数据
                                try:
                                    import io
                                    from PIL import Image
                                    import torch
                                    import numpy as np
                                    
                                    if potential_image.startswith('data:image'):
                                        potential_image = potential_image.split(',')[1]
                                    
                                    image_bytes = base64.b64decode(potential_image)
                                    pil_image = Image.open(io.BytesIO(image_bytes))
                                    image_array = np.array(pil_image).astype(np.float32) / 255.0
                                    if len(image_array.shape) == 3:
                                        image_tensor = torch.from_numpy(image_array).unsqueeze(0)
                                    else:
                                        image_tensor = torch.from_numpy(image_array)
                                    
                                    return (image_tensor, "base64_image", used_seed)
                                except Exception as e:
                                    print(f"[Image Generation] Failed to decode base64 image: {e}")
            
            return (None, f"Error: No image data found in API response. Available keys: {list(response_data.keys())}", -1)
            
        except requests.exceptions.RequestException as e:
            return (None, f"API request failed: {e}", -1)
        except Exception as e:
            return (None, f"An unexpected error occurred: {e}", -1)