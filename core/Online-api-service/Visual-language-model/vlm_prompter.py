import time
import openai
import sys
import os

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 导入工具类
utils_path = os.path.join(current_dir, "..", "utils.py")
import importlib.util
spec = importlib.util.spec_from_file_location("utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
encode_image_to_base64 = utils.encode_image_to_base64

# -------------------------------------------------------------------
# VLM Prompter 节点
# -------------------------------------------------------------------
class UltimateVLMPrompterNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): return time.time()
    @classmethod
    def INPUT_TYPES(s): return {"required": {"api_key":("API_KEY",), "base_url":("BASE_URL",), "model_name":("MODEL_NAME",),"image":("IMAGE",),"text_prompt":("STRING", {"multiline": True}),"seed":("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),"max_attempts":("INT", {"default": 3, "min": 1, "max": 10}),"retry_delay":("FLOAT", {"default": 2.0, "min": 0.0, "max": 60.0, "step": 0.5}),},"optional": {"system_prompt": ("STRING", {"forceInput": True}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("generated_text",); FUNCTION = "generate_vlm_text"; CATEGORY = "Magic Nodes/LLM"
    def generate_vlm_text(self, api_key, base_url, model_name, image, text_prompt, seed, max_attempts, retry_delay, system_prompt=None):
        if not all([api_key, base_url, model_name, image is not None, text_prompt]): return ("Error: One or more required inputs are missing.",)
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        try: base64_image = encode_image_to_base64(image)
        except Exception as e: return (f"Error encoding image: {e}",)
        messages = [];
        if system_prompt: messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user","content": [{"type": "text", "text": text_prompt},{"type": "image_url", "image_url": {"url": base64_image}}]})
        last_exception = None
        for attempt in range(max_attempts):
            try:
                print(f"[VLM Prompter] Attempt {attempt + 1}/{max_attempts} for model '{model_name}'..."); chat_completion = client.chat.completions.create(messages=messages, model=model_name, temperature=0.7, seed=seed, max_tokens=1024)
                generated_text = chat_completion.choices[0].message.content.strip(); print(f"[VLM Prompter] Attempt {attempt + 1} succeeded."); return (generated_text,)
            except Exception as e:
                last_exception = e; print(f"!!! [VLM Prompter] Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1: print(f"    Retrying in {retry_delay}s..."); time.sleep(retry_delay)
        return (f"Error: All {max_attempts} attempts failed. Last error: {last_exception}",) 