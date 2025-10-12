class GetLayerInfoNode:
    """获取图层信息节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图层": ("LAYER",),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "INT", "INT", "INT", "INT", "FLOAT", "FLOAT", "FLOAT", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("名称", "图层ID", "X坐标", "Y坐标", "宽度", "高度", "锚点X", "锚点Y", "不透明度", "可见性", "混合模式", "图像路径")
    FUNCTION = "get_layer_info"
    CATEGORY = "AFA2D/图层编辑"
    
    def get_layer_info(self, **kwargs):
        """获取图层的详细信息"""
        # 参数映射
        layer = kwargs.get("图层")
        # 提取图层信息
        name = layer.get("name", "Unnamed Layer")
        layer_id = layer.get("layer_id", -1)
        
        # 支持新的position/size/anchor格式
        if "position" in layer:
            position = layer.get("position", [0, 0])
            x, y = position[0], position[1]
        else:
            # 兼容旧格式
            x = layer.get("x", 0)
            y = layer.get("y", 0)
        
        if "size" in layer:
            size = layer.get("size", [0, 0])
            width, height = size[0], size[1]
        else:
            # 兼容旧格式
            width = layer.get("width", 0)
            height = layer.get("height", 0)
        
        if "anchor" in layer:
            anchor = layer.get("anchor", [0.0, 0.0])
            anchor_x, anchor_y = anchor[0], anchor[1]
        else:
            # 默认锚点
            anchor_x, anchor_y = 0.0, 0.0
        
        opacity = layer.get("opacity", 1.0)
        visible = layer.get("visible", True)
        blend_mode = layer.get("blend_mode", "normal")
        image_path = layer.get("image_path", "")
        
        return (name, layer_id, x, y, width, height, anchor_x, anchor_y, opacity, visible, blend_mode, image_path)