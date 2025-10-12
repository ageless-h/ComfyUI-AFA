import copy


class DeleteLayerNode:
    """删除图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
                "图层ID": ("INT", {"default": 0, "min": 0, "max": 999}),
            }
        }
    
    RETURN_TYPES = ("DOCUMENT",)
    RETURN_NAMES = ("更新后的文档",)
    FUNCTION = "delete_layer"
    CATEGORY = "AFA2D/图层编辑"
    
    def delete_layer(self, **kwargs):
        """从文档中删除指定ID的图层"""
        # 参数映射
        document = kwargs.get("文档")
        layer_id = kwargs.get("图层ID")
        # 深拷贝文档以避免修改原对象
        updated_document = copy.deepcopy(document)
        
        # 查找并删除指定ID的图层
        layers = updated_document["layers"]
        original_count = len(layers)
        
        # 过滤掉指定ID的图层
        updated_document["layers"] = [layer for layer in layers if layer["layer_id"] != layer_id]
        
        # 检查是否成功删除
        deleted_count = original_count - len(updated_document["layers"])
        if deleted_count > 0:
            print(f"Successfully deleted {deleted_count} layer(s) with ID {layer_id}")
        else:
            print(f"No layer found with ID {layer_id}")
        
        return (updated_document,)