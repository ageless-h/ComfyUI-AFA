import torch
import numpy as np
from PIL import Image
import os
import sys

# 添加混合模式模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from blend_modes import BlendModes


class PreviewLayerNode:
    """预览图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图层": ("LAYER",),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图层图像",)
    FUNCTION = "preview_layer"
    CATEGORY = "AFA2D/图层工具"
    OUTPUT_NODE = True
    
    def preview_layer(self, **kwargs):
        """预览单个图层，输出图层的效果图"""
        # 参数映射
        layer = kwargs.get("图层")
        # 检查图层可见性
        visible = layer.get("visible", True)
        if not visible:
            # 如果图层不可见，返回透明图像
            if "size" in layer:
                size = layer.get("size", [64, 64])
                width, height = size[0], size[1]
            else:
                # 兼容旧格式
                width = layer.get("width", 64)
                height = layer.get("height", 64)
            
            # 创建透明图像（全黑表示不可见）
            transparent_image = Image.new("RGB", (width, height), (0, 0, 0))
            image_array = np.array(transparent_image).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_array)[None,]
            return (image_tensor,)
        
        # 优先使用image_data，如果没有则尝试image_path（向后兼容）
        image_data = layer.get("image_data")
        if image_data is not None:
            # 直接使用tensor数据
            if isinstance(image_data, torch.Tensor):
                # 转换tensor为PIL图像
                image_array = (image_data.cpu().numpy() * 255).astype(np.uint8)
                layer_image = Image.fromarray(image_array, "RGBA")
            else:
                # 创建空白图像
                blank_image = Image.new("RGB", (64, 64), (128, 128, 128))
                image_array = np.array(blank_image).astype(np.float32) / 255.0
                image_tensor = torch.from_numpy(image_array)[None,]
                return (image_tensor,)
        else:
            # 向后兼容：尝试从文件路径加载
            image_path = layer.get("image_path")
            
            if not image_path or not os.path.exists(image_path):
                # 如果没有图像路径或文件不存在，创建一个空白图像
                bbox = layer.get("bbox", [0, 0, 64, 64])
                width = max(bbox[2] - bbox[0], 64)
                height = max(bbox[3] - bbox[1], 64)
                
                # 创建空白图像
                blank_image = Image.new("RGB", (width, height), (128, 128, 128))
                image_array = np.array(blank_image).astype(np.float32) / 255.0
                image_tensor = torch.from_numpy(image_array)[None,]
                return (image_tensor,)
            
            try:
                # 加载图层图像
                layer_image = Image.open(image_path).convert("RGBA")
            except Exception as e:
                print(f"Error loading image from path {image_path}: {e}")
                # 创建空白图像
                blank_image = Image.new("RGB", (64, 64), (128, 128, 128))
                image_array = np.array(blank_image).astype(np.float32) / 255.0
                image_tensor = torch.from_numpy(image_array)[None,]
                return (image_tensor,)
        
        try:
            
            # 获取透明度
            opacity = layer.get("opacity", 1.0)
            
            # 单图层预览：只应用透明度，不应用混合模式
            # 混合模式只在多图层合成时才有意义
            if opacity < 1.0:
                # 应用透明度
                layer_array = np.array(layer_image).astype(np.float32) / 255.0
                if layer_array.shape[-1] == 4:  # RGBA
                    layer_array[..., 3] *= opacity  # 调整alpha通道
                else:  # RGB，添加alpha通道
                    alpha_channel = np.full((*layer_array.shape[:2], 1), opacity, dtype=np.float32)
                    layer_array = np.concatenate([layer_array, alpha_channel], axis=-1)
                
                # 创建白色背景用于显示
                background = np.ones_like(layer_array)
                background[..., 3] = 1.0  # 背景完全不透明
                
                # 简单的alpha合成（不是混合模式）
                alpha = layer_array[..., 3:4]
                result_rgb = layer_array[..., :3] * alpha + background[..., :3] * (1 - alpha)
                
                # 转换为RGB格式
                result_array = np.clip(result_rgb * 255, 0, 255).astype(np.uint8)
                result_image = Image.fromarray(result_array, "RGB")
            else:
                # 透明度为1.0，直接显示图层
                # 创建白色背景用于显示透明区域
                background = Image.new("RGB", layer_image.size, (255, 255, 255))
                if layer_image.mode == "RGBA":
                    background.paste(layer_image, (0, 0), layer_image)
                    result_image = background
                else:
                    result_image = layer_image.convert("RGB")
            
            # 转换为ComfyUI格式的tensor
            image_array = np.array(result_image).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_array)[None,]  # 添加batch维度
            
            return (image_tensor,)
            
        except Exception as e:
            print(f"Error loading layer image from {image_path}: {e}")
            
            # 出错时返回错误提示图像
            error_image = Image.new("RGB", (256, 256), (255, 0, 0))
            image_array = np.array(error_image).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_array)[None,]
            return (image_tensor,)