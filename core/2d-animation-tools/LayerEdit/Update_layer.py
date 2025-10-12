import torch
import numpy as np
from PIL import Image
import os
import tempfile
import uuid
import copy


class UpdateLayerNode:
    """更新图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图层": ("LAYER",),
            },
            "optional": {
                "新图像": ("IMAGE",),
                "新名称": ("STRING", {"default": ""}),
                "新X坐标": ("INT", {"default": 0, "min": -8192, "max": 8192}),
                "新Y坐标": ("INT", {"default": 0, "min": -8192, "max": 8192}),
                "新锚点X": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "新锚点Y": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "新不透明度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "新可见性": ("BOOLEAN", {"default": True}),
                "新混合模式": (["正常", "正片叠底", "滤色", "叠加", "柔光", "强光", "颜色减淡", "颜色加深", "变暗", "变亮", "差值", "排除"], {"default": "正常"}),
            }
        }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("更新后的图层",)
    FUNCTION = "update_layer"
    CATEGORY = "AFA2D/图层编辑"
    
    def update_layer(self, **kwargs):
        """更新图层对象的属性"""
        # 参数映射
        layer = kwargs.get("图层")
        new_image = kwargs.get("新图像")
        new_name = kwargs.get("新名称", "")
        new_x = kwargs.get("新X坐标", -999999)
        new_y = kwargs.get("新Y坐标", -999999)
        new_anchor_x = kwargs.get("新锚点X", -1.0)
        new_anchor_y = kwargs.get("新锚点Y", -1.0)
        new_opacity = kwargs.get("新不透明度", -1.0)
        new_visible = kwargs.get("新可见性", True)
        new_blend_mode_cn = kwargs.get("新混合模式", "")
        
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
        new_blend_mode = blend_mode_map.get(new_blend_mode_cn, "normal")
        
        # 深拷贝原图层以避免修改原对象
        updated_layer = copy.deepcopy(layer)
        
        # 更新图像
        if new_image is not None:
            # 处理新图像
            if new_image.dim() == 4:
                new_image = new_image.squeeze(0)  # 移除batch维度
            
            # 转换为RGBA格式的tensor
            if new_image.shape[-1] == 3:
                # 如果是RGB，添加alpha通道
                alpha_channel = torch.ones((*new_image.shape[:-1], 1), dtype=new_image.dtype, device=new_image.device)
                new_image = torch.cat([new_image, alpha_channel], dim=-1)
            
            # 直接存储图像tensor数据
            updated_layer["image_data"] = new_image
            updated_layer["image_path"] = None  # 清除旧的文件路径
            
            # 更新尺寸
            height, width = new_image.shape[:2]
            
            # 更新size字段，支持新旧格式
            if "size" in updated_layer:
                updated_layer["size"] = [width, height]
            else:
                # 兼容旧格式
                updated_layer["width"] = width
                updated_layer["height"] = height
        
        # 更新名称
        if new_name:
            updated_layer["name"] = new_name
        
        # 更新位置（支持新旧格式）
        if "position" in updated_layer:
            # 新格式：使用position数组
            updated_layer["position"] = [new_x, new_y]
        else:
            # 兼容旧格式
            updated_layer["x"] = new_x
            updated_layer["y"] = new_y
        
        # 更新锚点
        if "anchor" in updated_layer:
            # 新格式：使用anchor数组
            updated_layer["anchor"] = [new_anchor_x, new_anchor_y]
        else:
            # 如果是旧格式，添加anchor字段
            updated_layer["anchor"] = [new_anchor_x, new_anchor_y]
        
        # 更新透明度
        updated_layer["opacity"] = new_opacity
        
        # 更新可见性
        updated_layer["visible"] = new_visible
        
        # 更新混合模式
        updated_layer["blend_mode"] = new_blend_mode
        
        return (updated_layer,)