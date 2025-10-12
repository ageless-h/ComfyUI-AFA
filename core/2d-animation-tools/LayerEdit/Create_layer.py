import torch
import numpy as np
from PIL import Image
import tempfile
import os


class CreateLayerNode:
    """创建图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "名称": ("STRING", {"default": "新图层"}),
                "X坐标": ("INT", {"default": 0, "min": -9999, "max": 9999}),
                "Y坐标": ("INT", {"default": 0, "min": -9999, "max": 9999}),
            },
            "optional": {
                "锚点X": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "锚点Y": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "不透明度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "可见性": ("BOOLEAN", {"default": True}),
                "混合模式": (["正常", "正片叠底", "滤色", "叠加", "柔光", "强光", "颜色减淡", "颜色加深", "变暗", "变亮", "差值", "排除"], {"default": "正常"}),
            }
        }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("图层",)
    FUNCTION = "create_layer"
    CATEGORY = "AFA2D/图层编辑"
    
    def create_layer(self, **kwargs):
        """创建新图层"""
        # 参数映射
        image = kwargs.get("图像")
        name = kwargs.get("名称")
        x = kwargs.get("X坐标")
        y = kwargs.get("Y坐标")
        anchor_x = kwargs.get("锚点X", 0.0)
        anchor_y = kwargs.get("锚点Y", 0.0)
        opacity = kwargs.get("不透明度", 1.0)
        visible = kwargs.get("可见性", True)
        blend_mode_cn = kwargs.get("混合模式", "正常")
        
        # 混合模式中英文映射
        blend_mode_map = {
            "正常": "normal",
            "正片叠底": "multiply",
            "滤色": "screen",
            "叠加": "overlay",
            "柔光": "soft_light",
            "强光": "hard_light",
            "颜色减淡": "color_dodge",
            "颜色加深": "color_burn",
            "变暗": "darken",
            "变亮": "lighten",
            "差值": "difference",
            "排除": "exclusion"
        }
        blend_mode = blend_mode_map.get(blend_mode_cn, "normal")
        # 转换图像格式
        if isinstance(image, torch.Tensor):
            # 从ComfyUI张量转换为PIL图像
            if image.dim() == 4:
                image = image.squeeze(0)  # 移除批次维度
            
            # 转换为numpy数组
            image_np = image.cpu().numpy()
            
            # 确保值在0-255范围内
            if image_np.max() <= 1.0:
                image_np = (image_np * 255).astype(np.uint8)
            else:
                image_np = image_np.astype(np.uint8)
            
            # 转换为PIL图像
            pil_image = Image.fromarray(image_np)
        else:
            pil_image = image
        
        # 获取图像尺寸
        width, height = pil_image.size
        
        # 将PIL图像转换为numpy数组，然后转换为tensor
        image_array = np.array(pil_image.convert("RGBA")).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_array)
        
        # 创建图层对象（直接存储图像数据）
        layer = {
            "layer_id": -1,  # 未分配ID
            "name": name,
            "image_data": image_tensor,  # 直接存储图像tensor数据
            "image_path": None,  # 保留兼容性，但不使用
            "mask_path": None,
            "position": [x, y],  # [x, y] 坐标
            "size": [width, height],  # [width, height] 尺寸
            "anchor": [anchor_x, anchor_y],  # [x, y] 锚点，范围 0.0-1.0
            "opacity": opacity,
            "visible": visible,
            "blend_mode": blend_mode,
            "metadata": {
                "created_by": "CreateLayerNode",
                "data_type": "tensor"
            }
        }
        
        return (layer,)