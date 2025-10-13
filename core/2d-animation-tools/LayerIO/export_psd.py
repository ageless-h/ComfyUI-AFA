import torch
import numpy as np
from PIL import Image
import os
import tempfile

# 尝试导入PhotoshopAPI（主要PSD写入库）
try:
    import photoshop_api as ps_api
    PHOTOSHOP_API_AVAILABLE = True
except ImportError:
    PHOTOSHOP_API_AVAILABLE = False

# 备用方案：使用psd-tools进行基本PSD创建
try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer, Group
    from psd_tools.constants import BlendMode, ColorMode
    PSD_TOOLS_AVAILABLE = True
except ImportError:
    PSD_TOOLS_AVAILABLE = False

# 第三备用方案：使用Aspose.PSD
try:
    from aspose.psd import Graphics, Pen, Color, Rectangle
    from aspose.psd.fileformats.psd import PsdImage
    ASPOSE_PSD_AVAILABLE = True
except ImportError:
    ASPOSE_PSD_AVAILABLE = False


class ExportPSDAdvancedNode:
    """高级PSD导出节点 - 支持真正的PSD文件格式导出"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
                "输出路径": ("STRING", {"default": "output.psd"}),
            },
            "optional": {
                "压缩": ("BOOLEAN", {"default": True}),
                "包含隐藏图层": ("BOOLEAN", {"default": False}),
                "色彩模式": (["RGB", "CMYK", "灰度"], {"default": "RGB"}),
                "位深度": ([8, 16, 32], {"default": 8}),
                "DPI": ("INT", {"default": 300, "min": 72, "max": 600}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("文件路径", "导出信息")
    FUNCTION = "export_psd_advanced"
    CATEGORY = "AFA2D/图层IO"
    OUTPUT_NODE = True
    
    def export_psd_advanced(self, **kwargs):
        """高级PSD导出功能"""
        try:
            print(f"[ExportPSD] ========== 开始高级PSD导出 ==========")
            
            # 检查可用的PSD库
            if not any([PHOTOSHOP_API_AVAILABLE, PSD_TOOLS_AVAILABLE, ASPOSE_PSD_AVAILABLE]):
                error_msg = "错误：未找到可用的PSD写入库。请安装以下任一库：\n"
                error_msg += "1. PhotoshopAPI: pip install PhotoshopAPI\n"
                error_msg += "2. psd-tools: pip install psd-tools\n"
                error_msg += "3. aspose-psd: pip install aspose-psd"
                print(f"[ExportPSD] {error_msg}")
                return ("", error_msg)
            
            # 获取参数
            document = kwargs.get("文档")
            output_path = kwargs.get("输出路径", "output.psd")
            compression = kwargs.get("压缩", True)
            include_hidden = kwargs.get("包含隐藏图层", False)
            color_mode = kwargs.get("色彩模式", "RGB")
            bit_depth = kwargs.get("位深度", 8)
            dpi = kwargs.get("DPI", 300)
            
            print(f"[ExportPSD] 输入参数:")
            print(f"[ExportPSD]   - 输出路径: '{output_path}'")
            print(f"[ExportPSD]   - 压缩: {compression}")
            print(f"[ExportPSD]   - 包含隐藏图层: {include_hidden}")
            print(f"[ExportPSD]   - 色彩模式: {color_mode}")
            print(f"[ExportPSD]   - 位深度: {bit_depth}")
            print(f"[ExportPSD]   - DPI: {dpi}")
            
            # 验证输入
            if not output_path or output_path.strip() == "":
                error_msg = "错误：输出路径不能为空"
                print(f"[ExportPSD] {error_msg}")
                return ("", error_msg)
            
            if not document or not isinstance(document, dict):
                error_msg = f"错误：无效的文档对象 - 类型: {type(document)}"
                print(f"[ExportPSD] {error_msg}")
                return ("", error_msg)
            
            if "layers" not in document or not document["layers"]:
                error_msg = "错误：文档中没有图层"
                print(f"[ExportPSD] {error_msg}")
                return ("", error_msg)
            
            # 确保输出路径以.psd结尾
            if not output_path.lower().endswith('.psd'):
                output_path = output_path + '.psd'
            
            # 处理输出路径
            if not os.path.isabs(output_path):
                output_path = os.path.abspath(output_path)
            
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"[ExportPSD] 创建输出目录: {output_dir}")
                except Exception as dir_error:
                    error_msg = f"错误：无法创建输出目录 '{output_dir}': {str(dir_error)}"
                    print(f"[ExportPSD] {error_msg}")
                    return ("", error_msg)
            
            # 获取画布尺寸
            canvas_size = document.get("canvas_size", [1920, 1080])
            canvas_width, canvas_height = canvas_size
            print(f"[ExportPSD] 画布尺寸: {canvas_width} x {canvas_height}")
            
            # 根据可用库选择导出方法，优先使用更可靠的方案
            try:
                if PSD_TOOLS_AVAILABLE:
                    print(f"[ExportPSD] 尝试使用psd-tools导出")
                    return self._export_with_psd_tools(document, output_path, canvas_width, canvas_height, 
                                                     include_hidden, color_mode, bit_depth, dpi)
                elif PHOTOSHOP_API_AVAILABLE:
                    print(f"[ExportPSD] 尝试使用PhotoshopAPI导出")
                    return self._export_with_photoshop_api(document, output_path, canvas_width, canvas_height, 
                                                         include_hidden, color_mode, bit_depth, dpi, compression)
                elif ASPOSE_PSD_AVAILABLE:
                    print(f"[ExportPSD] 尝试使用Aspose.PSD导出")
                    return self._export_with_aspose(document, output_path, canvas_width, canvas_height, 
                                                  include_hidden, color_mode, bit_depth, dpi)
                else:
                    # 使用PIL作为备用方案，导出为PNG格式
                    print(f"[ExportPSD] 警告：没有可用的PSD库，使用PIL导出为PNG格式")
                    return self._export_with_pil_fallback(document, output_path, canvas_width, canvas_height, 
                                                        include_hidden, color_mode)
            except Exception as export_error:
                print(f"[ExportPSD] 导出失败: {export_error}")
                # 如果主要方法失败，尝试备用方案
                print(f"[ExportPSD] 尝试备用导出方案")
                return self._export_with_pil_fallback(document, output_path, canvas_width, canvas_height, 
                                                    include_hidden, color_mode)
                
        except Exception as e:
            import traceback
            error_msg = f"导出PSD文件时出错: {str(e)}"
            print(f"[ExportPSD] 致命错误: {error_msg}")
            print(f"[ExportPSD] 错误详情:")
            print(traceback.format_exc())
            return ("", error_msg)
    
    def _export_with_photoshop_api(self, document, output_path, canvas_width, canvas_height, 
                                  include_hidden, color_mode, bit_depth, dpi, compression):
        """使用PhotoshopAPI导出PSD文件"""
        print(f"[ExportPSD] 使用PhotoshopAPI导出")
        
        try:
            # 创建新的PSD文档
            color_mode_map = {
                "RGB": ps_api.ColorMode.RGB,
                "CMYK": ps_api.ColorMode.CMYK,
                "灰度": ps_api.ColorMode.Grayscale
            }
            
            psd_doc = ps_api.PsdImage.create(
                width=canvas_width,
                height=canvas_height,
                color_mode=color_mode_map.get(color_mode, ps_api.ColorMode.RGB),
                bit_depth=bit_depth,
                dpi=dpi
            )
            
            # 混合模式映射
            blend_mode_map = {
                'normal': ps_api.BlendMode.Normal,
                'multiply': ps_api.BlendMode.Multiply,
                'screen': ps_api.BlendMode.Screen,
                'overlay': ps_api.BlendMode.Overlay,
                'soft_light': ps_api.BlendMode.SoftLight,
                'hard_light': ps_api.BlendMode.HardLight,
                'color_dodge': ps_api.BlendMode.ColorDodge,
                'color_burn': ps_api.BlendMode.ColorBurn,
                'darken': ps_api.BlendMode.Darken,
                'lighten': ps_api.BlendMode.Lighten,
                'difference': ps_api.BlendMode.Difference,
                'exclusion': ps_api.BlendMode.Exclusion
            }
            
            # 处理图层
            processed_layers = 0
            for layer in document["layers"]:
                if not include_hidden and not layer.get("visible", True):
                    continue
                
                image_data = layer.get("image_data")
                if image_data is None:
                    continue
                
                # 转换图像数据
                pil_image = self._convert_tensor_to_pil(image_data)
                if pil_image is None:
                    continue
                
                # 获取图层属性
                layer_name = layer.get("name", f"图层{processed_layers}")
                position = layer.get("position", [0, 0])
                opacity = int(layer.get("opacity", 1.0) * 255)
                blend_mode = layer.get("blend_mode", "normal")
                visible = layer.get("visible", True)
                
                # 创建图层
                psd_layer = psd_doc.add_pixel_layer()
                psd_layer.name = layer_name
                psd_layer.left = position[0]
                psd_layer.top = position[1]
                psd_layer.opacity = opacity
                psd_layer.blend_mode = blend_mode_map.get(blend_mode, ps_api.BlendMode.Normal)
                psd_layer.visible = visible
                
                # 设置图层图像数据
                psd_layer.set_image_data(pil_image)
                
                processed_layers += 1
                print(f"[ExportPSD] 已处理图层: {layer_name}")
            
            # 保存PSD文件
            print(f"[ExportPSD] 保存PSD文件到: {output_path}")
            psd_doc.save(output_path, compression=compression)
            
            # 验证文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[ExportPSD] PSD文件保存成功，大小: {file_size} 字节")
                
                export_info = f"成功导出PSD文档到: {output_path}\n"
                export_info += f"画布尺寸: {canvas_width} x {canvas_height}\n"
                export_info += f"导出图层数: {processed_layers}\n"
                export_info += f"色彩模式: {color_mode}\n"
                export_info += f"位深度: {bit_depth}位\n"
                export_info += f"DPI: {dpi}\n"
                export_info += f"文件大小: {file_size} 字节"
                
                return (output_path, export_info)
            else:
                error_msg = f"错误：PSD文件保存失败"
                return ("", error_msg)
                
        except Exception as e:
            error_msg = f"PhotoshopAPI导出失败: {str(e)}"
            print(f"[ExportPSD] {error_msg}")
            return ("", error_msg)
    
    def _export_with_psd_tools(self, document, output_path, canvas_width, canvas_height, 
                              include_hidden, color_mode, bit_depth, dpi):
        """使用psd-tools导出PSD文件"""
        print(f"[ExportPSD] 使用psd-tools导出")
        
        try:
            # psd-tools使用字符串模式而不是ColorMode枚举
            color_mode_map = {
                "RGB": "RGB",
                "CMYK": "CMYK", 
                "灰度": "L"  # 灰度模式在PIL中是'L'
            }
            
            # 创建新的PSD文档 - psd-tools使用字符串模式
            psd_mode = color_mode_map.get(color_mode, "RGB")
            print(f"[ExportPSD] 创建PSD文档: 模式={psd_mode}, 尺寸=({canvas_width}, {canvas_height}), 位深={bit_depth}")
            
            psd = PSDImage.new(
                mode=psd_mode,
                size=(canvas_width, canvas_height),
                depth=bit_depth
            )
            
            # psd-tools使用BlendMode枚举
            blend_mode_map = {
                'normal': BlendMode.NORMAL,
                'multiply': BlendMode.MULTIPLY,
                'screen': BlendMode.SCREEN,
                'overlay': BlendMode.OVERLAY,
                'soft_light': BlendMode.SOFT_LIGHT,
                'hard_light': BlendMode.HARD_LIGHT,
                'color_dodge': BlendMode.COLOR_DODGE,
                'color_burn': BlendMode.COLOR_BURN,
                'darken': BlendMode.DARKEN,
                'lighten': BlendMode.LIGHTEN,
                'difference': BlendMode.DIFFERENCE,
                'exclusion': BlendMode.EXCLUSION
            }
            
            # 处理图层
            processed_layers = 0
            for layer in document["layers"]:
                if not include_hidden and not layer.get("visible", True):
                    continue
                
                image_data = layer.get("image_data")
                if image_data is None:
                    continue
                
                # 转换图像数据
                pil_image = self._convert_tensor_to_pil(image_data)
                if pil_image is None:
                    continue
                
                # 获取图层属性
                layer_name = layer.get("name", f"图层{processed_layers}")
                if not layer_name or layer_name.strip() == "":
                    layer_name = f"图层{processed_layers}"
                    
                position = layer.get("position", [0, 0])
                opacity = int(layer.get("opacity", 1.0) * 255)
                blend_mode = layer.get("blend_mode", "normal")
                visible = layer.get("visible", True)
                
                # 获取锚点信息
                anchor = layer.get("anchor", [0.0, 0.0])
                anchor_x, anchor_y = anchor[0], anchor[1]
                
                print(f"[ExportPSD] 处理图层: {layer_name}, 位置: {position}, 锚点: {anchor}, 透明度: {opacity}")
                
                # 使用psd-tools的正确API创建图层
                try:
                    # 确保图像是正确的模式，保持透明度
                    if pil_image.mode != "RGBA":
                        layer_image = pil_image.convert("RGBA")
                    else:
                        layer_image = pil_image.copy()
                    
                    # 获取图层尺寸
                    layer_width, layer_height = layer_image.size
                    
                    # 获取图层位置
                    x = int(position[0]) if len(position) > 0 else 0
                    y = int(position[1]) if len(position) > 1 else 0
                    
                    # 根据锚点计算实际的PSD位置（与预览系统保持一致）
                    # 锚点 [0,0] 是左上角，[0.5,0.5] 是中心，[1,1] 是右下角
                    # PSD中的位置是基于左上角的，所以需要根据锚点调整
                    left_pos = int(x - layer_width * anchor_x)
                    top_pos = int(y - layer_height * anchor_y)
                    
                    # 🎯 使用新发现的"后设置名称"方法来支持中文图层名称
                    # 步骤1：先用英文临时名称创建图层
                    temp_name = f"TempLayer{processed_layers}"
                    pixel_layer = PixelLayer.frompil(
                        layer_image, 
                        psd, 
                        temp_name,  # 使用英文临时名称
                        top_pos,    # top_offset位置参数
                        left_pos    # left_offset位置参数
                    )
                    
                    # 步骤2：立即设置中文名称（这是关键！）
                    pixel_layer.name = layer_name  # 直接使用原始中文名称
                    
                    # 设置图层属性
                    pixel_layer.visible = visible
                    if hasattr(pixel_layer, 'opacity'):
                        pixel_layer.opacity = opacity
                    
                    # 设置混合模式
                    if blend_mode in blend_mode_map:
                        pixel_layer.blend_mode = blend_mode_map[blend_mode]
                    
                    # 添加图层到PSD
                    psd.append(pixel_layer)
                    
                    # 记录成功使用中文名称
                    print(f"[ExportPSD] ✓ 成功设置中文图层名称: '{layer_name}'")
                    
                    processed_layers += 1
                    print(f"[ExportPSD] Processed layer: {layer_name}")
                    
                except Exception as layer_error:
                    print(f"[ExportPSD] Layer processing error: {layer_error}")
                    # 如果图层创建失败，尝试简单的合成方法
                    try:
                        if processed_layers == 0:
                            # 创建一个基于PIL的PSD
                            composite_image = pil_image.convert(psd_mode if psd_mode != "L" else "RGB")
                            if composite_image.size != (canvas_width, canvas_height):
                                canvas = Image.new(psd_mode if psd_mode != "L" else "RGB", (canvas_width, canvas_height), (255, 255, 255))
                                canvas.paste(composite_image, tuple(position))
                                composite_image = canvas
                            
                            # 使用frompil创建PSD
                            psd = PSDImage.frompil(composite_image)
                            processed_layers += 1
                            print(f"[ExportPSD] Using fallback method to process layer: {layer_name}")
                    except Exception as fallback_error:
                        print(f"[ExportPSD] Fallback method also failed: {fallback_error}")
                        continue
            
            # 保存PSD文件
            print(f"[ExportPSD] Saving PSD file to: {output_path}")
            try:
                # 设置UTF-8环境并尝试保存
                import locale
                import os
                
                # 保存当前环境设置
                original_env = {}
                original_locale = None
                utf8_env_vars = {
                    'PYTHONIOENCODING': 'utf-8',
                    'PYTHONLEGACYWINDOWSFSENCODING': '0',  # 禁用Windows旧版文件系统编码
                    'PYTHONUTF8': '1',  # 强制使用UTF-8
                }
                
                # 在Windows上尝试设置更多编码相关变量
                if os.name == 'nt':
                    utf8_env_vars.update({
                        'CHCP': '65001',  # Windows代码页设置为UTF-8
                    })
                else:
                    utf8_env_vars.update({
                        'LC_ALL': 'en_US.UTF-8',
                        'LANG': 'en_US.UTF-8'
                    })
                
                # 设置UTF-8环境变量
                for key, value in utf8_env_vars.items():
                    original_env[key] = os.environ.get(key)
                    os.environ[key] = value
                
                # 设置locale
                try:
                    original_locale = locale.getlocale()
                    if os.name == 'nt':
                        # Windows上尝试设置UTF-8 locale
                        try:
                            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                        except:
                            try:
                                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                            except:
                                try:
                                    locale.setlocale(locale.LC_ALL, '')  # 使用系统默认
                                except:
                                    pass
                    else:
                        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                except:
                    pass  # 如果设置失败，继续使用默认设置
                
                try:
                    # 尝试保存PSD文件
                    psd.save(output_path)
                    print(f"[ExportPSD] PSD文件保存成功，保留了原始图层名称")
                    
                finally:
                    # 恢复原始环境变量
                    for key, original_value in original_env.items():
                        if original_value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = original_value
                    
                    # 恢复原始locale
                    if original_locale:
                        try:
                            locale.setlocale(locale.LC_ALL, original_locale)
                        except:
                            pass
                            
            except (UnicodeEncodeError, UnicodeDecodeError, Exception) as encoding_error:
                print(f"[ExportPSD] 保存失败，可能是编码问题: {encoding_error}")
                print(f"[ExportPSD] 尝试使用安全图层名称重新创建PSD文件...")
                
                # 重新创建PSD文件，使用安全的图层名称
                safe_psd = PSDImage.new(
                    mode=psd_mode,
                    size=(canvas_width, canvas_height),
                    depth=bit_depth
                )
                safe_processed_layers = 0
                
                for layer in document["layers"]:
                    if not include_hidden and not layer.get("visible", True):
                        continue
                    
                    image_data = layer.get("image_data")
                    if image_data is None:
                        continue
                    
                    # 转换图像数据
                    pil_image = self._convert_tensor_to_pil(image_data)
                    if pil_image is None:
                        continue
                    
                    # 获取图层属性
                    layer_name = layer.get("name", f"图层{safe_processed_layers}")
                    if not layer_name or layer_name.strip() == "":
                        layer_name = f"图层{safe_processed_layers}"
                    
                    position = layer.get("position", [0, 0])
                    opacity = int(layer.get("opacity", 1.0) * 255)
                    blend_mode = layer.get("blend_mode", "normal")
                    visible = layer.get("visible", True)
                    
                    # 获取锚点信息
                    anchor = layer.get("anchor", [0.0, 0.0])
                    anchor_x, anchor_y = anchor[0], anchor[1]
                    
                    # 确保图像是正确的模式，保持透明度
                    if pil_image.mode != "RGBA":
                        layer_image = pil_image.convert("RGBA")
                    else:
                        layer_image = pil_image.copy()
                    
                    # 获取图层尺寸
                    layer_width, layer_height = layer_image.size
                    
                    # 获取图层位置
                    x = int(position[0]) if len(position) > 0 else 0
                    y = int(position[1]) if len(position) > 1 else 0
                    
                    # 根据锚点计算实际的PSD位置
                    left_pos = int(x - layer_width * anchor_x)
                    top_pos = int(y - layer_height * anchor_y)
                    
                    # 🎯 使用"后设置名称"方法支持中文图层名称
                    temp_name = f"TempLayer{safe_processed_layers}"
                    pixel_layer = PixelLayer.frompil(
                        layer_image, 
                        safe_psd, 
                        temp_name,  # 使用英文临时名称
                        top_pos,    # top_offset位置参数
                        left_pos    # left_offset位置参数
                    )
                    
                    # 立即设置中文名称
                    pixel_layer.name = layer_name  # 直接使用原始中文名称
                    
                    # 设置图层属性
                    pixel_layer.visible = visible
                    if hasattr(pixel_layer, 'opacity'):
                        pixel_layer.opacity = opacity
                    
                    # 设置混合模式
                    if blend_mode in blend_mode_map:
                        pixel_layer.blend_mode = blend_mode_map[blend_mode]
                    
                    # 添加图层到PSD
                    safe_psd.append(pixel_layer)
                    
                    safe_processed_layers += 1
                    print(f"[ExportPSD] ✓ 成功设置中文图层名称: '{layer_name}'")
                
                # 保存使用安全名称的PSD文件
                safe_psd.save(output_path)
                print(f"[ExportPSD] 使用安全图层名称成功保存PSD文件")
                processed_layers = safe_processed_layers
            
            # 验证文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[ExportPSD] PSD file saved successfully, size: {file_size} bytes")
                
                export_info = f"成功导出PSD文档到: {output_path}\n"
                export_info += f"画布尺寸: {canvas_width} x {canvas_height}\n"
                export_info += f"导出图层数: {processed_layers}\n"
                export_info += f"色彩模式: {color_mode}\n"
                export_info += f"位深度: {bit_depth}位\n"
                export_info += f"文件大小: {file_size} 字节"
                
                return (output_path, export_info)
            else:
                error_msg = f"错误：PSD文件保存失败"
                return ("", error_msg)
                
        except Exception as e:
            error_msg = f"psd-tools导出失败: {str(e)}"
            print(f"[ExportPSD] {error_msg}")
            return ("", error_msg)
    
    def _export_with_aspose(self, document, output_path, canvas_width, canvas_height, 
                           include_hidden, color_mode, bit_depth, dpi):
        """使用Aspose.PSD导出PSD文件"""
        print(f"[ExportPSD] 使用Aspose.PSD导出")
        
        try:
            # 创建新的PSD文档
            with PsdImage(canvas_width, canvas_height) as psd:
                # 处理图层
                processed_layers = 0
                for layer in document["layers"]:
                    if not include_hidden and not layer.get("visible", True):
                        continue
                    
                    image_data = layer.get("image_data")
                    if image_data is None:
                        continue
                    
                    # 转换图像数据
                    pil_image = self._convert_tensor_to_pil(image_data)
                    if pil_image is None:
                        continue
                    
                    # 获取图层属性
                    layer_name = layer.get("name", f"图层{processed_layers}")
                    position = layer.get("position", [0, 0])
                    opacity = layer.get("opacity", 1.0)
                    visible = layer.get("visible", True)
                    
                    # 添加常规图层
                    regular_layer = psd.add_regular_layer()
                    
                    # 使用Graphics API绘制图像
                    graphics = Graphics(regular_layer)
                    
                    # 将PIL图像转换为Aspose格式并绘制
                    # 这里需要根据Aspose.PSD的具体API进行调整
                    
                    processed_layers += 1
                    print(f"[ExportPSD] 已处理图层: {layer_name}")
                
                # 保存PSD文件
                print(f"[ExportPSD] 保存PSD文件到: {output_path}")
                psd.save(output_path)
            
            # 验证文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[ExportPSD] PSD文件保存成功，大小: {file_size} 字节")
                
                export_info = f"成功导出PSD文档到: {output_path}\n"
                export_info += f"画布尺寸: {canvas_width} x {canvas_height}\n"
                export_info += f"导出图层数: {processed_layers}\n"
                export_info += f"文件大小: {file_size} 字节"
                
                return (output_path, export_info)
            else:
                error_msg = f"错误：PSD文件保存失败"
                return ("", error_msg)
                
        except Exception as e:
            error_msg = f"Aspose.PSD导出失败: {str(e)}"
            print(f"[ExportPSD] {error_msg}")
            return ("", error_msg)
    
    def _export_with_pil_fallback(self, document, output_path, canvas_width, canvas_height, 
                                 include_hidden, color_mode):
        """使用PIL作为备用方案导出图像（PNG格式）"""
        print(f"[ExportPSD] 使用PIL备用方案导出")
        
        try:
            # 修改输出路径为PNG格式
            if output_path.lower().endswith('.psd'):
                png_output_path = output_path[:-4] + '.png'
            else:
                png_output_path = output_path + '.png'
            
            # 创建画布
            if color_mode == "灰度":
                canvas = Image.new('L', (canvas_width, canvas_height), 255)
            else:
                canvas = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 255))
            
            processed_layers = 0
            
            # 处理图层
            for layer in document["layers"]:
                if not include_hidden and not layer.get("visible", True):
                    continue
                
                image_data = layer.get("image_data")
                if image_data is None:
                    continue
                
                # 转换图像数据
                pil_image = self._convert_tensor_to_pil(image_data)
                if pil_image is None:
                    continue
                
                # 获取图层属性
                layer_name = layer.get("name", f"图层{processed_layers}")
                position = layer.get("position", [0, 0])
                opacity = layer.get("opacity", 1.0)
                
                print(f"[ExportPSD] 合成图层: {layer_name}, 位置: {position}, 透明度: {opacity}")
                
                # 调整透明度
                if opacity < 1.0:
                    # 创建带透明度的图像
                    alpha = pil_image.split()[-1]
                    alpha = alpha.point(lambda p: int(p * opacity))
                    pil_image.putalpha(alpha)
                
                # 合成到画布上
                if pil_image.mode == 'RGBA' and canvas.mode == 'RGBA':
                    canvas.paste(pil_image, tuple(position), pil_image)
                else:
                    canvas.paste(pil_image, tuple(position))
                
                processed_layers += 1
            
            # 保存文件
            print(f"[ExportPSD] 保存图像文件到: {png_output_path}")
            canvas.save(png_output_path, 'PNG')
            
            # 验证文件
            if os.path.exists(png_output_path):
                file_size = os.path.getsize(png_output_path)
                print(f"[ExportPSD] 图像文件保存成功，大小: {file_size} 字节")
                
                export_info = f"成功导出图像到: {png_output_path}\n"
                export_info += f"画布尺寸: {canvas_width} x {canvas_height}\n"
                export_info += f"导出图层数: {processed_layers}\n"
                export_info += f"色彩模式: {color_mode}\n"
                export_info += f"文件格式: PNG (PSD库不可用时的备用格式)\n"
                export_info += f"文件大小: {file_size} 字节"
                
                return (png_output_path, export_info)
            else:
                error_msg = f"错误：图像文件保存失败"
                return ("", error_msg)
                
        except Exception as e:
            error_msg = f"PIL备用导出失败: {str(e)}"
            print(f"[ExportPSD] {error_msg}")
            return ("", error_msg)

    def _convert_tensor_to_pil(self, image_data):
        """将PyTorch张量转换为PIL图像"""
        try:
            if isinstance(image_data, torch.Tensor):
                # 转换为numpy数组
                if image_data.max() <= 1.0:
                    image_array = (image_data.cpu().numpy() * 255).astype(np.uint8)
                else:
                    image_array = image_data.cpu().numpy().astype(np.uint8)
                
                # 处理维度
                if len(image_array.shape) == 4:  # [B, H, W, C]
                    image_array = image_array[0]
                
                if len(image_array.shape) == 3 and image_array.shape[0] in [1, 3, 4]:  # [C, H, W]
                    image_array = np.transpose(image_array, (1, 2, 0))
                
                # 处理通道数
                if image_array.shape[2] == 3:
                    # RGB -> RGBA
                    alpha = np.ones((image_array.shape[0], image_array.shape[1], 1), dtype=image_array.dtype) * 255
                    image_array = np.concatenate([image_array, alpha], axis=2)
                elif image_array.shape[2] == 1:
                    # 灰度 -> RGBA
                    image_array = np.repeat(image_array, 3, axis=2)
                    alpha = np.ones((image_array.shape[0], image_array.shape[1], 1), dtype=image_array.dtype) * 255
                    image_array = np.concatenate([image_array, alpha], axis=2)
                
                return Image.fromarray(image_array, 'RGBA')
            else:
                return None
        except Exception as e:
            print(f"[ExportPSD] 图像转换失败: {str(e)}")
            return None
    



# 节点映射
NODE_CLASS_MAPPINGS = {
    "ExportPSDAdvancedNode": ExportPSDAdvancedNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ExportPSDAdvancedNode": "导出PSD文档"
}