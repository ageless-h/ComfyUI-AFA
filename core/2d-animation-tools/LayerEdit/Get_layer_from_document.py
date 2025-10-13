class GetLayerFromDocumentNode:
    """从文档获取图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
            },
            "optional": {
                "图层ID": ("INT", {"default": 0, "min": -1, "max": 999}),
            }
        }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("图层",)
    FUNCTION = "get_layer_from_document"
    CATEGORY = "AFA2D/图层编辑"
    
    def get_layer_from_document(self, 文档, 图层ID=0):
        """从文档中获取指定的图层"""
        try:
            document = 文档
            
            # 如果指定了图层ID，使用ID查找
            if 图层ID >= 0:
                # 按图层ID查找
                for layer in document.layers:
                    if layer.get("layer_id") == 图层ID:
                        return (layer,)
                print(f"未找到ID为 {图层ID} 的图层")
                return (None,)
            
            # 如果图层ID为-1，返回第一个图层
            if document.layers:
                return (document.layers[0],)
            else:
                print("文档中没有图层")
                return (None,)
                
        except Exception as e:
            print(f"获取图层时出错: {str(e)}")
            return (None,)