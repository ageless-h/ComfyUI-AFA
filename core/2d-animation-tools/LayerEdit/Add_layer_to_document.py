import copy


class AddLayerToDocumentNode:
    """添加图层到文档节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
                "图层": ("LAYER",),
            },
            "optional": {
                "目标图层ID": ("INT", {"default": 0, "min": -1, "max": 999}),
            }
        }
    
    RETURN_TYPES = ("DOCUMENT",)
    RETURN_NAMES = ("更新后的文档",)
    FUNCTION = "add_layer_to_document"
    CATEGORY = "AFA2D/图层编辑"
    
    def add_layer_to_document(self, **kwargs):
        """将图层添加到文档中，由文档分配ID"""
        # 参数映射
        document = kwargs.get("文档")
        layer = kwargs.get("图层")
        target_layer_id = kwargs.get("目标图层ID", 0)
        # 深拷贝文档和图层以避免修改原对象
        updated_document = copy.deepcopy(document)
        new_layer = copy.deepcopy(layer)
        
        # 获取现有图层ID列表
        existing_ids = [l["layer_id"] for l in updated_document["layers"]]
        
        # 分配新的图层ID
        if target_layer_id >= 0 and target_layer_id not in existing_ids:
            # 使用指定的ID（如果可用）
            assigned_id = target_layer_id
        else:
            # 自动分配新ID，从0开始
            assigned_id = 0
            while assigned_id in existing_ids:
                assigned_id += 1
        
        # 设置图层ID
        new_layer["layer_id"] = assigned_id
        
        # 添加图层到文档
        updated_document["layers"].append(new_layer)
        
        print(f"Added layer '{new_layer.get('name', 'Unnamed')}' with ID {assigned_id}")
        
        return (updated_document,)