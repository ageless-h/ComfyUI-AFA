import torch
import numpy as np
from PIL import Image, ImageDraw
import os
import sys

# 添加混合模式模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from blend_modes import BlendModes


class PreviewDocumentNode:
    """预览文档节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
            },
            "optional": {
                "目标图层ID": ("INT", {"default": -1, "min": -1, "max": 999}),
                "显示所有图层": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("预览图像",)
    FUNCTION = "preview_document"
    CATEGORY = "AFA2D/图层工具"
    
    def preview_document(self, **kwargs):
        """预览文档，生成最终效果图或指定图层的效果图"""
        document = kwargs.get("文档")
        target_layer_id = kwargs.get("目标图层ID", -1)
        show_all_layers = kwargs.get("显示所有图层", True)
        
        canvas_width, canvas_height = document["canvas_size"]
        layers = document["layers"]
        
        # 创建画布
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
        
        # 渲染图层
        if show_all_layers:
            # 预览所有可见图层，按图层ID从小到大排序渲染（ID小的在下层，ID大的在上层）
            sorted_layers = sorted(layers, key=lambda x: x.get("layer_id", 0))
            
            for layer in sorted_layers:
                if layer.get("visible", True):
                    canvas = self._render_layer_with_blend(canvas, layer)
        elif target_layer_id >= 0:
            # 预览指定图层
            target_layer = None
            for layer in layers:
                if layer["layer_id"] == target_layer_id:
                    target_layer = layer
                    break
            
            if target_layer and target_layer.get("visible", True):
                canvas = self._render_layer_with_blend(canvas, target_layer)
        
        # 转换为RGB（移除alpha通道）
        if canvas.mode == "RGBA":
            background = Image.new("RGB", canvas.size, (255, 255, 255))
            background.paste(canvas, mask=canvas.split()[-1])
            canvas = background
        
        # 转换为ComfyUI格式的tensor
        canvas_array = np.array(canvas).astype(np.float32) / 255.0
        canvas_tensor = torch.from_numpy(canvas_array)[None,]
        
        return (canvas_tensor,)
    
    def _check_document_structure(self, document, diagnostic_report):
        """检查文档结构的完整性"""
        diagnostic_report.append("=== 文档结构检查 ===")
        
        # 检查必要字段
        required_fields = ["canvas_size", "layers"]
        for field in required_fields:
            if field in document:
                diagnostic_report.append(f"✓ 必要字段 '{field}' 存在")
            else:
                diagnostic_report.append(f"✗ 缺少必要字段 '{field}'")
        
        # 检查画布尺寸
        canvas_size = document.get("canvas_size", [0, 0])
        if isinstance(canvas_size, (list, tuple)) and len(canvas_size) >= 2:
            width, height = canvas_size[0], canvas_size[1]
            diagnostic_report.append(f"✓ 画布尺寸: {width}x{height}")
            if width <= 0 or height <= 0:
                diagnostic_report.append("✗ 画布尺寸无效（宽度或高度 <= 0）")
        else:
            diagnostic_report.append(f"✗ 画布尺寸格式错误: {canvas_size}")
        
        # 检查图层
        layers = document.get("layers", [])
        diagnostic_report.append(f"图层总数: {len(layers)}")
        
        for i, layer in enumerate(layers):
            diagnostic_report.append(f"--- 图层 {i+1} 检查 ---")
            
            # 检查图层基本信息
            layer_name = layer.get("name", f"Layer_{i}")
            layer_id = layer.get("layer_id", "未设置")
            visible = layer.get("visible", True)
            
            diagnostic_report.append(f"  名称: {layer_name}")
            diagnostic_report.append(f"  ID: {layer_id}")
            diagnostic_report.append(f"  可见性: {visible}")
            
            # 检查图像数据
            has_image_data = "image_data" in layer
            has_image_path = "image_path" in layer
            
            if has_image_data:
                image_data = layer["image_data"]
                if isinstance(image_data, torch.Tensor):
                    diagnostic_report.append(f"  ✓ 图像数据: Tensor {image_data.shape}")
                else:
                    diagnostic_report.append(f"  ✓ 图像数据: {type(image_data)}")
            elif has_image_path:
                diagnostic_report.append(f"  ✓ 图像路径: {layer['image_path']}")
            else:
                diagnostic_report.append("  ✗ 缺少图像数据（image_data 或 image_path）")
            
            # 检查位置信息
            if "position" in layer:
                position = layer["position"]
                if isinstance(position, dict):
                    x = position.get("x", 0)
                    y = position.get("y", 0)
                    diagnostic_report.append(f"  ✓ 位置: 字典格式 {{x: {x}, y: {y}}}")
                elif isinstance(position, (list, tuple)) and len(position) >= 2:
                    x, y = position[0], position[1]
                    diagnostic_report.append(f"  ✓ 位置: 列表格式 [{x}, {y}]")
                else:
                    diagnostic_report.append(f"  ✗ 位置格式错误: {position}")
            elif "x" in layer and "y" in layer:
                x = layer["x"]
                y = layer["y"]
                diagnostic_report.append(f"  ✓ 位置: 旧格式 x={x}, y={y}")
            else:
                diagnostic_report.append("  ✗ 缺少位置信息")
            
            # 检查混合模式和不透明度
            blend_mode = layer.get("blend_mode", "normal")
            opacity = layer.get("opacity", 1.0)
            diagnostic_report.append(f"  混合模式: {blend_mode}")
            diagnostic_report.append(f"  不透明度: {opacity}")
            
            if opacity < 0 or opacity > 1:
                diagnostic_report.append("  ⚠ 不透明度超出正常范围 [0, 1]")
        
        diagnostic_report.append("=== 文档结构检查完成 ===")
    
    def _render_layer(self, canvas, layer):
        """渲染单个图层到画布上"""
        # 检查图层可见性
        if not layer.get("visible", True):
            return canvas
    
    def _render_layer_with_blend(self, canvas, layer):
        """渲染单个图层到画布上，支持混合模式"""
        # 检查图层可见性
        if not layer.get("visible", True):
            return canvas
            
        # 优先使用image_data，如果没有则尝试image_path（向后兼容）
        image_data = layer.get("image_data")
        
        if image_data is not None:
            # 直接使用tensor数据
            if isinstance(image_data, torch.Tensor):
                # 移除batch维度（如果存在）
                if len(image_data.shape) == 4:
                    image_data = image_data.squeeze(0)
                
                # 转换为numpy数组
                image_array = image_data.cpu().numpy()
                
                # 确保值在0-1范围内，然后转换为0-255
                image_array = np.clip(image_array, 0, 1)
                image_array = (image_array * 255).astype(np.uint8)
                
                # 根据通道数处理
                if image_array.shape[2] == 4:
                    # RGBA
                    layer_image = Image.fromarray(image_array, 'RGBA')
                elif image_array.shape[2] == 3:
                    # RGB转换为RGBA
                    rgba_array = np.zeros((image_array.shape[0], image_array.shape[1], 4), dtype=np.uint8)
                    rgba_array[:, :, :3] = image_array
                    rgba_array[:, :, 3] = 255  # 设置alpha为不透明
                    layer_image = Image.fromarray(rgba_array, 'RGBA')
                elif image_array.shape[2] == 1:
                    # 灰度转换为RGBA
                    rgba_array = np.zeros((image_array.shape[0], image_array.shape[1], 4), dtype=np.uint8)
                    rgba_array[:, :, :3] = np.repeat(image_array, 3, axis=2)
                    rgba_array[:, :, 3] = 255  # 设置alpha为不透明
                    layer_image = Image.fromarray(rgba_array, 'RGBA')
                else:
                    raise ValueError(f"不支持的图像通道数: {image_array.shape[2]}")
            else:
                layer_image = image_data
        else:
            # 向后兼容：尝试从文件路径加载
            image_path = layer.get("image_path")
            if not image_path or not os.path.exists(image_path):
                return canvas
            try:
                layer_image = Image.open(image_path).convert("RGBA")
            except Exception:
                return canvas

        try:
            # 获取位置信息（支持多种格式）
            if "position" in layer:
                position = layer.get("position", [0, 0])
                if isinstance(position, dict):
                    x = position.get("x", 0)
                    y = position.get("y", 0)
                elif isinstance(position, (list, tuple)) and len(position) >= 2:
                    x, y = position[0], position[1]
                else:
                    x, y = 0, 0
            else:
                # 兼容旧格式
                x = layer.get("x", 0)
                y = layer.get("y", 0)
            
            # 获取锚点信息并计算实际位置
            anchor = layer.get("anchor", [0.0, 0.0])
            anchor_x, anchor_y = anchor[0], anchor[1]
            
            # 获取图层尺寸
            layer_width, layer_height = layer_image.size
            
            # 根据锚点计算实际粘贴位置
            # 锚点 [0,0] 是左上角，[0.5,0.5] 是中心，[1,1] 是右下角
            actual_x = int(x - layer_width * anchor_x)
            actual_y = int(y - layer_height * anchor_y)
            
            # 获取混合模式和透明度
            blend_mode = layer.get("blend_mode", "normal")
            opacity = layer.get("opacity", 1.0)
            
            # 创建一个与画布同样大小的临时图层
            temp_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            
            # 将图层图像粘贴到临时图层的正确位置
            if (actual_x < canvas.size[0] and actual_y < canvas.size[1] and 
                actual_x + layer_width > 0 and actual_y + layer_height > 0):
                temp_layer.paste(layer_image, (actual_x, actual_y), layer_image)
            
            # 应用混合模式
            if blend_mode != "normal" and blend_mode != "正常":
                try:
                    # 转换为numpy数组进行混合
                    canvas_array = np.array(canvas).astype(np.float32) / 255.0
                    temp_array = np.array(temp_layer).astype(np.float32) / 255.0
                    
                    # 中英文混合模式映射
                    blend_mode_map = {
                        "正常": "normal",
                        "叠加": "overlay", 
                        "柔光": "soft_light",
                        "强光": "hard_light",
                        "颜色减淡": "color_dodge",
                        "颜色加深": "color_burn",
                        "变暗": "darken",
                        "变亮": "lighten",
                        "差值": "difference",
                        "排除": "exclusion",
                        "正片叠底": "multiply",
                        "滤色": "screen"
                    }
                    
                    # 获取英文混合模式名称
                    english_blend_mode = blend_mode_map.get(blend_mode, blend_mode)
                    
                    # 应用混合模式
                    blended_array = BlendModes.apply_blend_mode(
                        canvas_array, temp_array, english_blend_mode, opacity
                    )
                    
                    # 转换回PIL图像
                    blended_array = np.clip(blended_array * 255, 0, 255).astype(np.uint8)
                    canvas = Image.fromarray(blended_array, "RGBA")
                    
                except Exception:
                    # 回退到普通渲染
                    canvas = Image.alpha_composite(canvas, temp_layer)
            else:
                # 普通混合模式
                canvas = Image.alpha_composite(canvas, temp_layer)
            
        except Exception:
            # 出错时回退到普通渲染
            pass
        
        return canvas