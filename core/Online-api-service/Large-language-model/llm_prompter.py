import time
import openai

# -------------------------------------------------------------------
# LLM Prompter 节点
# -------------------------------------------------------------------
class UltimateLLMPrompterNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): return time.time()
    @classmethod
    def INPUT_TYPES(s): return {"required": {"api_key":("API_KEY",), "base_url":("BASE_URL",), "model_name":("MODEL_NAME",),"system_prompt":("STRING", {"forceInput": True}), "user_prompt":("STRING", {"forceInput": True}),"seed":("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),"max_attempts":("INT", {"default": 3, "min": 1, "max": 10}),"retry_delay":("FLOAT", {"default": 2.0, "min": 0.0, "max": 60.0, "step": 0.5}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("generated_text",); FUNCTION = "generate_text"; CATEGORY = "AFA/大模型"
    def generate_text(self, api_key, base_url, model_name, system_prompt, user_prompt, seed, max_attempts, retry_delay):
        if not all([api_key, base_url, model_name, system_prompt, user_prompt]): return ("Error: One or more required inputs are missing.",)
        if user_prompt.startswith("Error:"): return(user_prompt,)
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        last_exception = None
        for attempt in range(max_attempts):
            try:
                print(f"[LLM Prompter] Attempt {attempt + 1}/{max_attempts} for model '{model_name}'..."); chat_completion = client.chat.completions.create(messages=messages, model=model_name, temperature=0.7, seed=seed)
                generated_text = chat_completion.choices[0].message.content.strip(); print(f"[LLM Prompter] Attempt {attempt + 1} succeeded."); return (generated_text,)
            except Exception as e:
                last_exception = e; print(f"!!! [LLM Prompter] Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1: print(f"    Retrying in {retry_delay}s..."); time.sleep(retry_delay)
        return (f"Error: All {max_attempts} attempts failed. Last error: {last_exception}",) 