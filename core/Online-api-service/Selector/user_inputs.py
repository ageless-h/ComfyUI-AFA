import sys
import os

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
# 将项目根目录添加到sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)

# 导入工具类
utils_path = os.path.join(current_dir, "..", "utils.py")
import importlib.util
spec = importlib.util.spec_from_file_location("utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
format_user_prompt = utils.format_user_prompt

# -------------------------------------------------------------------
# 用户输入构建器节点
# -------------------------------------------------------------------
class WorldbuildingUserInputNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "项目名称": ("STRING", {"multiline": True}),
            "动画类型": ("STRING", {"multiline": True}),
            "核心创意": ("STRING", {"multiline": True}),
            "目标观众": ("STRING", {"multiline": True}),
            "整体基调": ("STRING", {"multiline": True}),
        }}
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_prompt",)
    FUNCTION = "build"
    CATEGORY = "AFA/输入"
    
    def build(self, **kwargs):
        return format_user_prompt("世界观构建", **kwargs)

class CharacterUserInputNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "项目名称": ("STRING", {"multiline": True}),
            "世界观概要": ("STRING", {"multiline": True}),
            "角色姓名": ("STRING", {"multiline": True}),
            "角色基本设定": ("STRING", {"multiline": True}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_prompt",)
    FUNCTION = "build"
    CATEGORY = "AFA/输入"

    def build(self, **kwargs):
        return format_user_prompt("角色档案构建", **kwargs)

class SaveTheCatUserInputNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "项目名称": ("STRING", {"multiline": True}),
            "核心创意": ("STRING", {"multiline": True}),
            "主角": ("STRING", {"multiline": True}),
            "核心冲突": ("STRING", {"multiline": True}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_prompt",)
    FUNCTION = "build"
    CATEGORY = "AFA/输入"

    def build(self, **kwargs):
        return format_user_prompt("救猫咪结构", **kwargs)

class ScreenwriterUserInputNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "故事大纲节点": ("STRING", {"multiline": True}),
            "场景目标": ("STRING", {"multiline": True}),
            "角色A": ("STRING", {"multiline": True}),
            "角色B": ("STRING", {"multiline": True}),
            "场景地点与时间": ("STRING", {"multiline": True}),
        }}
        
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_prompt",)
    FUNCTION = "build"
    CATEGORY = "AFA/输入"

    def build(self, **kwargs):
        return format_user_prompt("剧本场景撰写", **kwargs)

class StoryboardUserInputNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "剧本片段": ("STRING", {"multiline": True}),
            "场景情绪基调": ("STRING", {"multiline": True}),
            "视觉风格参考": ("STRING", {"multiline": True}),
        }}
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_prompt",)
    FUNCTION = "build"
    CATEGORY = "AFA/输入"

    def build(self, **kwargs):
        return format_user_prompt("分镜设计", **kwargs) 