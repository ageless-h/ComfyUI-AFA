import torch
import numpy as np
from PIL import Image
import os


class UnpackLayerNode:
    """解包图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图层": ("LAYER",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT", "INT", "INT", "FLOAT", "FLOAT", "FLOAT", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("图像", "名称", "X坐标", "Y坐标", "宽度", "高度", "锚点X", "锚点Y", "不透明度", "可见性", "混合模式", "元数据")
    FUNCTION = "unpack_layer"
    CATEGORY = "AFA2D/图层编辑"
    
    def unpack_layer(self, **kwargs):
        """解包图层对象，提取各个属性"""
        # 参数映射
        layer = kwargs.get("图层")
        # 提取基本属性（支持新旧格式）
        name = layer.get("name", "")
        
        # 支持新的position/size/anchor格式
        position = layer.get("position", [0, 0])
        size = layer.get("size", [64, 64])
        anchor = layer.get("anchor", [0.0, 0.0])
        
        x, y = position[0], position[1]
        width, height = size[0], size[1]
        anchor_x, anchor_y = anchor[0], anchor[1]
        
        # 兼容旧的bbox格式
        if "bbox" in layer and "position" not in layer:
            bbox = layer.get("bbox", [0, 0, 0, 0])
            x, y, width, height = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # 兼容旧的x, y, width, height格式
        if "x" in layer and "position" not in layer:
            x = layer.get("x", 0)
            y = layer.get("y", 0)
            width = layer.get("width", 64)
            height = layer.get("height", 64)
        
        opacity = layer.get("opacity", 1.0)
        visible = layer.get("visible", True)
        blend_mode = layer.get("blend_mode", "normal")
        metadata = str(layer.get("metadata", {}))
        
        # 处理图像 - 优先使用image_data
        image_data = layer.get("image_data")
        if image_data is not None and isinstance(image_data, torch.Tensor):
            # 直接使用tensor数据
            image_tensor = image_data
            # 确保有batch维度
            if image_tensor.dim() == 3:
                image_tensor = image_tensor.unsqueeze(0)
            # 转换为RGB格式（如果是RGBA）
            if image_tensor.shape[-1] == 4:
                image_tensor = image_tensor[..., :3]  # 移除alpha通道
        else:
            # 向后兼容：尝试从文件路径加载
            image_path = layer.get("image_path")
            if image_path and os.path.exists(image_path):
                try:
                    # 加载图像并转换为ComfyUI格式
                    pil_image = Image.open(image_path).convert("RGB")
                    image_array = np.array(pil_image).astype(np.float32) / 255.0
                    image_tensor = torch.from_numpy(image_array)[None,]  # 添加batch维度
                except Exception as e:
                    print(f"Error loading image from {image_path}: {e}")
                    # 创建空白图像
                    image_tensor = torch.zeros((1, height if height > 0 else 64, width if width > 0 else 64, 3))
            else:
                # 创建空白图像
                image_tensor = torch.zeros((1, height if height > 0 else 64, width if width > 0 else 64, 3))
        
        return (image_tensor, name, x, y, width, height, anchor_x, anchor_y, opacity, visible, blend_mode, metadata)