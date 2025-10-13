import torch
import numpy as np
from PIL import Image
import os
import uuid

try:
    from psd_tools import PSDImage
    PSD_AVAILABLE = True
except ImportError:
    PSD_AVAILABLE = False

try:
    import folder_paths
    FOLDER_PATHS_AVAILABLE = True
except ImportError:
    FOLDER_PATHS_AVAILABLE = False


class ImportPSDNode:
    """从PSD文件导入文档节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "PSD文件": ("STRING", {"default": "", "psd_upload": True, "hidden_input": True}),
                "保持原始尺寸": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("DOCUMENT", "STRING")
    RETURN_NAMES = ("文档", "导入信息")
    FUNCTION = "import_psd"
    CATEGORY = "AFA2D/图层IO"
    
    def import_psd(self, **kwargs):
        """从PSD文件导入文档"""
        # 检查psd-tools是否可用
        if not PSD_AVAILABLE:
            error_msg = "错误：需要安装psd-tools库。请运行: pip install psd-tools"
            return (None, error_msg)
        
        # 参数映射
        psd_file = kwargs.get("PSD文件", "")
        keep_original_size = kwargs.get("保持原始尺寸", True)
        
        # 处理文件路径 - 支持上传的文件名和完整路径
        if not psd_file:
            error_msg = "错误：请选择PSD文件"
            return (None, error_msg)
        
        # 如果是上传的文件名，构建完整路径
        if not os.path.isabs(psd_file):
            if FOLDER_PATHS_AVAILABLE:
                # 使用ComfyUI的input目录
                input_dir = folder_paths.get_input_directory()
                psd_path = os.path.join(input_dir, psd_file)
                
                # 如果文件不存在，尝试在psd子目录查找
                if not os.path.exists(psd_path):
                    psd_path = os.path.join(input_dir, "psd", psd_file)
            else:
                # 回退到当前目录
                psd_path = os.path.abspath(psd_file)
        else:
            psd_path = psd_file
        
        # 检查文件是否存在
        if not os.path.exists(psd_path):
            error_msg = f"错误：PSD文件不存在: {psd_path}"
            return (None, error_msg)
        
        try:
            # 打开PSD文件
            print(f"🔄 开始导入PSD文件: {psd_path}")
            psd = PSDImage.open(psd_path)
            print(f"✓ PSD文件打开成功，尺寸: {psd.width} x {psd.height}")
            
            # 输出PSD基本信息
            total_layers = len(list(psd))
            print(f"📊 PSD文件包含 {total_layers} 个顶级图层")
            
            # 获取画布尺寸（始终使用PSD原始尺寸）
            doc_width = psd.width
            doc_height = psd.height
            
            # 混合模式映射（PSD到内部格式）
            # 支持多种格式：普通格式、blendmode.前缀格式、下划线格式等
            blend_mode_map = {
                # 标准格式
                'normal': 'normal',
                'multiply': 'multiply',
                'screen': 'screen',
                'overlay': 'overlay',
                'soft-light': 'soft_light',
                'hard-light': 'hard_light',
                'color-dodge': 'color_dodge',
                'color-burn': 'color_burn',
                'darken': 'darken',
                'lighten': 'lighten',
                'difference': 'difference',
                'exclusion': 'exclusion',
                
                # blendmode.前缀格式
                'blendmode.normal': 'normal',
                'blendmode.multiply': 'multiply',
                'blendmode.screen': 'screen',
                'blendmode.overlay': 'overlay',
                'blendmode.soft_light': 'soft_light',
                'blendmode.hard_light': 'hard_light',
                'blendmode.color_dodge': 'color_dodge',
                'blendmode.color_burn': 'color_burn',
                'blendmode.darken': 'darken',
                'blendmode.lighten': 'lighten',
                'blendmode.difference': 'difference',
                'blendmode.exclusion': 'exclusion',
                
                # 其他可能的格式变体
                'soft_light': 'soft_light',
                'hard_light': 'hard_light',
                'color_dodge': 'color_dodge',
                'color_burn': 'color_burn',
                'softlight': 'soft_light',
                'hardlight': 'hard_light',
                'colordodge': 'color_dodge',
                'colorburn': 'color_burn',
            }
            
            # 创建文档对象
            document = {
                "document_id": str(uuid.uuid4()),
                "version": "1.0",
                "canvas_size": [doc_width, doc_height],
                "layers": [],
                "metadata": {
                    "created_by": "ImportPSDNode",
                    "source_file": psd_path,
                    "original_size": [psd.width, psd.height],
                    "description": f"从PSD文件导入: {os.path.basename(psd_path)}"
                }
            }
            
            # 递归处理图层
            layer_id_counter = 0
            
            def process_layer(psd_layer, parent_name=""):
                nonlocal layer_id_counter
                
                # 跳过不可见的图层
                if not psd_layer.visible:
                    return []
                
                layers = []
                
                # 处理图层组
                if hasattr(psd_layer, 'is_group') and psd_layer.is_group():
                    # 递归处理组内的图层
                    group_name = psd_layer.name if psd_layer.name else f"组{layer_id_counter}"
                    for child_layer in psd_layer:
                        child_layers = process_layer(child_layer, f"{parent_name}{group_name}/")
                        layers.extend(child_layers)
                else:
                    # 处理普通图层
                    try:
                        # 获取图层图像
                        layer_image = psd_layer.composite()
                        if layer_image is None:
                            return []
                        
                        # 转换为RGBA格式
                        if layer_image.mode != 'RGBA':
                            layer_image = layer_image.convert('RGBA')
                        
                        # 转换为tensor
                        image_array = np.array(layer_image).astype(np.float32) / 255.0
                        image_tensor = torch.from_numpy(image_array)
                        
                        # 获取图层属性
                        layer_name = psd_layer.name if psd_layer.name else f"图层{layer_id_counter}"
                        if parent_name:
                            layer_name = f"{parent_name}{layer_name}"
                        
                        # 获取图层位置和尺寸
                        bbox = psd_layer.bbox
                        if hasattr(bbox, 'x1'):
                            # bbox是一个对象，有x1, y1, width, height属性
                            x, y = bbox.x1, bbox.y1
                            width, height = bbox.width, bbox.height
                        else:
                            # bbox是一个tuple (left, top, right, bottom)
                            left, top, right, bottom = bbox
                            x, y = left, top
                            width, height = right - left, bottom - top
                        
                        # 获取不透明度
                        opacity = psd_layer.opacity / 255.0 if hasattr(psd_layer, 'opacity') else 1.0
                        
                        # 获取混合模式
                        def normalize_blend_mode(raw_blend_mode):
                            """智能处理混合模式名称，支持多种格式"""
                            if not raw_blend_mode:
                                return 'normal', 'normal'
                            
                            # 转换为小写字符串
                            mode_str = str(raw_blend_mode).lower().strip()
                            
                            # 直接查找映射表
                            if mode_str in blend_mode_map:
                                return mode_str, blend_mode_map[mode_str]
                            
                            # 尝试移除常见前缀
                            prefixes_to_remove = ['blendmode.', 'blend_mode.', 'blend.']
                            for prefix in prefixes_to_remove:
                                if mode_str.startswith(prefix):
                                    clean_mode = mode_str[len(prefix):]
                                    if clean_mode in blend_mode_map:
                                        return mode_str, blend_mode_map[clean_mode]
                            
                            # 尝试替换连字符为下划线
                            mode_with_underscore = mode_str.replace('-', '_')
                            if mode_with_underscore in blend_mode_map:
                                return mode_str, blend_mode_map[mode_with_underscore]
                            
                            # 尝试移除所有分隔符
                            mode_no_separators = mode_str.replace('-', '').replace('_', '').replace('.', '')
                            for mapped_mode, internal_mode in blend_mode_map.items():
                                if mapped_mode.replace('-', '').replace('_', '').replace('.', '') == mode_no_separators:
                                    return mode_str, internal_mode
                            
                            # 如果都没找到，返回normal
                            return mode_str, 'normal'
                        
                        blend_mode = 'normal'
                        psd_blend_mode = 'normal'
                        if hasattr(psd_layer, 'blend_mode'):
                            psd_blend_mode, blend_mode = normalize_blend_mode(psd_layer.blend_mode)
                            
                            # 输出混合模式转换日志
                            if blend_mode == 'normal' and psd_blend_mode.lower() != 'normal' and not psd_blend_mode.lower().endswith('.normal'):
                                print(f"⚠️ 图层 '{layer_name}': 未支持的混合模式 '{psd_blend_mode}' -> 使用 'normal'")
                            elif psd_blend_mode.lower() != 'normal' and not psd_blend_mode.lower().endswith('.normal'):
                                print(f"✓ 图层 '{layer_name}': 混合模式 '{psd_blend_mode}' -> '{blend_mode}'")
                        
                        # 创建图层对象
                        layer = {
                            "layer_id": layer_id_counter,
                            "name": layer_name,
                            "image_data": image_tensor,
                            "image_path": None,
                            "position": [x, y],
                            "size": [width, height],
                            "anchor": [0.0, 0.0],  # PSD默认左上角锚点
                            "opacity": opacity,
                            "visible": psd_layer.visible,
                            "blend_mode": blend_mode,
                            "metadata": {
                                "created_by": "ImportPSDNode",
                                "data_type": "tensor",
                                "source_layer": psd_layer.name,
                                "original_blend_mode": psd_blend_mode,
                                "psd_opacity": psd_layer.opacity if hasattr(psd_layer, 'opacity') else 255,
                                "bbox": str(bbox),
                                "layer_kind": str(psd_layer.kind) if hasattr(psd_layer, 'kind') else 'unknown'
                            }
                        }
                        
                        layers.append(layer)
                        layer_id_counter += 1
                        
                    except Exception as e:
                        print(f"警告：处理图层 '{psd_layer.name}' 时出错: {str(e)}")
                        pass
                
                return layers
            
            # 处理所有图层
            all_layers = []
            print(f"\n🔄 开始处理图层...")
            for layer in psd:
                processed_layers = process_layer(layer)
                all_layers.extend(processed_layers)
            
            # 将图层添加到文档
            document["layers"] = all_layers
            
            # 输出处理总结
            print(f"✅ 图层处理完成，共处理 {len(all_layers)} 个图层")
            
            # 统计混合模式使用情况
            blend_mode_count = {}
            for layer in all_layers:
                mode = layer.get('blend_mode', 'normal')
                blend_mode_count[mode] = blend_mode_count.get(mode, 0) + 1
            
            print(f"📈 混合模式分布:")
            for mode, count in sorted(blend_mode_count.items()):
                print(f"   {mode}: {count} 个图层")
            
            # 生成详细的导入信息
            import_info = f"=== PSD导入详细信息 ===\n"
            import_info += f"文件: {os.path.basename(psd_path)}\n"
            import_info += f"画布尺寸: {doc_width} x {doc_height}\n"
            import_info += f"原始尺寸: {psd.width} x {psd.height}\n"
            import_info += f"图层总数: {len(all_layers)}\n\n"
            
            # 添加混合模式统计
            blend_mode_stats = {}
            for layer in all_layers:
                blend_mode = layer.get('blend_mode', 'normal')
                blend_mode_stats[blend_mode] = blend_mode_stats.get(blend_mode, 0) + 1
            
            import_info += f"=== 混合模式统计 ===\n"
            for mode, count in blend_mode_stats.items():
                import_info += f"  {mode}: {count}个图层\n"
            
            import_info += f"\n=== 图层详细信息 ===\n"
            for i, layer in enumerate(all_layers):
                metadata = layer.get('metadata', {})
                import_info += f"图层 {i+1}: {layer['name']}\n"
                import_info += f"  位置: {layer['position']}, 尺寸: {layer['size']}\n"
                import_info += f"  不透明度: {layer['opacity']:.2f}"
                
                # 显示原始PSD不透明度
                psd_opacity = metadata.get('psd_opacity', 255)
                if psd_opacity != 255:
                    import_info += f" (PSD: {psd_opacity}/255)"
                
                import_info += f"\n  混合模式: {layer['blend_mode']}"
                
                # 显示原始混合模式（如果不同）
                original_blend = metadata.get('original_blend_mode', 'normal')
                if original_blend.lower() != layer['blend_mode']:
                    import_info += f" (原始: {original_blend})"
                
                import_info += f"\n  可见性: {layer['visible']}\n"
                
                # 显示图层类型
                layer_kind = metadata.get('layer_kind', 'unknown')
                if layer_kind != 'unknown':
                    import_info += f"  图层类型: {layer_kind}\n"
                
                # 显示边界框信息
                bbox_info = metadata.get('bbox', '')
                if bbox_info:
                    import_info += f"  边界框: {bbox_info}\n"
                
                # 检查是否有未映射的混合模式
                if original_blend.lower() not in blend_mode_map:
                    import_info += f"  ⚠️ 警告: 未支持的混合模式 '{original_blend}'\n"
                
                # 显示图像数据信息
                if 'image_data' in layer and layer['image_data'] is not None:
                    img_shape = layer['image_data'].shape
                    import_info += f"  图像数据: {img_shape} (tensor)\n"
                
                import_info += "\n"
            
            # 添加支持的混合模式列表
            import_info += f"=== 支持的混合模式 ===\n"
            for psd_mode, internal_mode in blend_mode_map.items():
                import_info += f"  {psd_mode} -> {internal_mode}\n"
            
            return (document, import_info)
            
        except Exception as e:
            error_msg = f"导入PSD文件时出错: {str(e)}"
            return (None, error_msg)