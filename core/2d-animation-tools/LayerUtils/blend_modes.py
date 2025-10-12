"""
混合模式实现模块
实现各种图层混合模式的像素级算法
"""

import numpy as np
from PIL import Image

# 尝试导入torch，如果失败则使用numpy替代
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class BlendModes:
    """混合模式实现类"""
    
    @staticmethod
    def _ensure_numpy(image):
        """确保输入是numpy数组格式"""
        if isinstance(image, Image.Image):
            return np.array(image, dtype=np.float32) / 255.0
        elif HAS_TORCH and hasattr(image, 'dim'):  # torch.Tensor
            if image.dim() == 4:  # BHWC
                image = image.squeeze(0)
            if image.dim() == 3 and image.shape[0] in [1, 3, 4]:  # CHW
                image = image.permute(1, 2, 0)
            return image.cpu().numpy().astype(np.float32)
        elif isinstance(image, np.ndarray):
            if image.dtype == np.uint8:
                return image.astype(np.float32) / 255.0
            return image.astype(np.float32)
        else:
            raise ValueError(f"不支持的图像格式: {type(image)}")
    
    @staticmethod
    def _clamp(array):
        """将数值限制在0-1范围内"""
        return np.clip(array, 0.0, 1.0)
    
    @staticmethod
    def normal(base, overlay, opacity=1.0):
        """正常混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        # 确保两个图像有相同的通道数
        if base.shape[-1] == 3 and overlay.shape[-1] == 4:
            # 如果base是RGB，overlay是RGBA，给base添加alpha通道
            alpha = np.ones((*base.shape[:2], 1), dtype=np.float32)
            base = np.concatenate([base, alpha], axis=-1)
        elif base.shape[-1] == 4 and overlay.shape[-1] == 3:
            # 如果base是RGBA，overlay是RGB，给overlay添加alpha通道
            alpha = np.ones((*overlay.shape[:2], 1), dtype=np.float32)
            overlay = np.concatenate([overlay, alpha], axis=-1)
        
        # 应用透明度
        if overlay.shape[-1] == 4:
            overlay_alpha = overlay[..., 3:4] * opacity
            result = base[..., :3] * (1 - overlay_alpha) + overlay[..., :3] * overlay_alpha
            if base.shape[-1] == 4:
                result_alpha = base[..., 3:4] + overlay_alpha * (1 - base[..., 3:4])
                result = np.concatenate([result, result_alpha], axis=-1)
        else:
            result = base * (1 - opacity) + overlay * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def multiply(base, overlay, opacity=1.0):
        """正片叠底混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        # 处理RGB通道
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = base_rgb * overlay_rgb
        
        # 处理alpha通道
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            # 应用混合模式和透明度
            final_alpha = overlay_alpha * opacity
            # 正确的混合：在有alpha的区域使用混合结果，在没有alpha的区域保持原始
            blended_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([blended_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def screen(base, overlay, opacity=1.0):
        """滤色混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = 1 - (1 - base_rgb) * (1 - overlay_rgb)
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def overlay(base, overlay, opacity=1.0):
        """叠加混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        # 叠加算法：如果base < 0.5，使用multiply*2，否则使用1-2*(1-base)*(1-overlay)
        mask = base_rgb < 0.5
        result_rgb = np.where(mask, 
                             2 * base_rgb * overlay_rgb,
                             1 - 2 * (1 - base_rgb) * (1 - overlay_rgb))
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def soft_light(base, overlay, opacity=1.0):
        """柔光混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        # 柔光算法
        mask = overlay_rgb < 0.5
        result_rgb = np.where(mask,
                             base_rgb - (1 - 2 * overlay_rgb) * base_rgb * (1 - base_rgb),
                             base_rgb + (2 * overlay_rgb - 1) * (np.sqrt(base_rgb) - base_rgb))
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def hard_light(base, overlay, opacity=1.0):
        """强光混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        # 强光算法：如果overlay < 0.5，使用multiply*2，否则使用screen
        mask = overlay_rgb < 0.5
        result_rgb = np.where(mask,
                             2 * base_rgb * overlay_rgb,
                             1 - 2 * (1 - base_rgb) * (1 - overlay_rgb))
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def color_dodge(base, overlay, opacity=1.0):
        """颜色减淡混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        # 颜色减淡算法：base / (1 - overlay)，正确处理边界情况
        result_rgb = np.where(overlay_rgb <= 0.0, 0.0,
                             np.where(overlay_rgb >= 1.0, 1.0,
                                     np.minimum(1.0, base_rgb / (1.0 - overlay_rgb))))
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def color_burn(base, overlay, opacity=1.0):
        """颜色加深混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        # 颜色加深算法：1 - (1 - base) / overlay，正确处理除零情况
        result_rgb = np.where(overlay_rgb <= 0.0, 0.0,
                             np.where(overlay_rgb >= 1.0, base_rgb,
                                     np.maximum(0.0, 1.0 - (1.0 - base_rgb) / overlay_rgb)))
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def darken(base, overlay, opacity=1.0):
        """变暗混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = np.minimum(base_rgb, overlay_rgb)
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def lighten(base, overlay, opacity=1.0):
        """变亮混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = np.maximum(base_rgb, overlay_rgb)
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def difference(base, overlay, opacity=1.0):
        """差值混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = np.abs(base_rgb - overlay_rgb)
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def exclusion(base, overlay, opacity=1.0):
        """排除混合模式"""
        base = BlendModes._ensure_numpy(base)
        overlay = BlendModes._ensure_numpy(overlay)
        
        base_rgb = base[..., :3] if base.shape[-1] >= 3 else base
        overlay_rgb = overlay[..., :3] if overlay.shape[-1] >= 3 else overlay
        
        result_rgb = base_rgb + overlay_rgb - 2 * base_rgb * overlay_rgb
        
        if base.shape[-1] == 4 or overlay.shape[-1] == 4:
            base_alpha = base[..., 3:4] if base.shape[-1] == 4 else np.ones((*base.shape[:2], 1))
            overlay_alpha = overlay[..., 3:4] if overlay.shape[-1] == 4 else np.ones((*overlay.shape[:2], 1))
            
            final_alpha = overlay_alpha * opacity
            result_rgb = base_rgb * (1 - final_alpha) + result_rgb * final_alpha
            result_alpha = base_alpha + final_alpha * (1 - base_alpha)
            result = np.concatenate([result_rgb, result_alpha], axis=-1)
        else:
            result = base_rgb * (1 - opacity) + result_rgb * opacity
        
        return BlendModes._clamp(result)
    
    @staticmethod
    def apply_blend_mode(base, overlay, mode, opacity=1.0):
        """应用指定的混合模式"""
        # 中英文混合模式映射
        mode_mapping = {
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
            "排除": "exclusion",
            # 英文名称
            "normal": "normal",
            "multiply": "multiply",
            "screen": "screen", 
            "overlay": "overlay",
            "soft_light": "soft_light",
            "hard_light": "hard_light",
            "color_dodge": "color_dodge",
            "color_burn": "color_burn",
            "darken": "darken",
            "lighten": "lighten",
            "difference": "difference",
            "exclusion": "exclusion"
        }
        
        # 获取英文模式名
        english_mode = mode_mapping.get(mode, "normal")
        
        # 调用对应的混合模式函数
        blend_functions = {
            "normal": BlendModes.normal,
            "multiply": BlendModes.multiply,
            "screen": BlendModes.screen,
            "overlay": BlendModes.overlay,
            "soft_light": BlendModes.soft_light,
            "hard_light": BlendModes.hard_light,
            "color_dodge": BlendModes.color_dodge,
            "color_burn": BlendModes.color_burn,
            "darken": BlendModes.darken,
            "lighten": BlendModes.lighten,
            "difference": BlendModes.difference,
            "exclusion": BlendModes.exclusion
        }
        
        blend_func = blend_functions.get(english_mode, BlendModes.normal)
        return blend_func(base, overlay, opacity)