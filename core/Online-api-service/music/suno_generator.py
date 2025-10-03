import os
import json
import time
import re
import requests
import numpy as np
import torch
import tempfile
import torchaudio
import comfy.utils
import io
import base64

# 创建音频对象的辅助函数
def create_audio_object(url, max_duration_seconds=20):
    """创建ComfyUI可用的音频对象
    
    Args:
        url: 音频URL，如果为空则创建空音频
        max_duration_seconds: 最大音频长度（秒）
    """
    if not url:
        # 创建一个空的音频对象，确保维度正确
        # ComfyUI期望的格式是 [batch, channels, samples] - 必须是3D
        sample_rate = 16000
        waveform = torch.zeros((1, 1, int(sample_rate * max_duration_seconds)), dtype=torch.float32)  # [batch=1, 单声道, max_duration秒]
        return {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
    
    try:
        # 下载音频文件
        print(f"[Suno生成器] 开始下载音频: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 保存为临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
            
        print(f"[Suno生成器] 音频已保存到临时文件: {temp_path}")
        
        # 使用torchaudio加载音频
        try:
            # 加载音频文件
            waveform, sample_rate = torchaudio.load(temp_path)
            print(f"[Suno生成器] 音频加载成功，原始形状: {waveform.shape}, 采样率: {sample_rate}")
            
            # 关键修复：确保波形始终是2D张量 [channels, samples]，然后转换为3D
            if len(waveform.shape) == 1:
                # 1D -> 2D: 添加通道维度
                waveform = waveform.unsqueeze(0)
                print(f"[Suno生成器] 1D转2D: {waveform.shape}")
            elif len(waveform.shape) == 0:
                # 0D -> 2D: 创建单个样本
                waveform = waveform.unsqueeze(0).unsqueeze(0)
                print(f"[Suno生成器] 0D转2D: {waveform.shape}")
            elif len(waveform.shape) > 2:
                # 多维 -> 2D: 只保留前两个维度
                waveform = waveform[:2] if waveform.shape[0] <= 2 else waveform[:2]
                print(f"[Suno生成器] 多维转2D: {waveform.shape}")
            
            # 确保第一个维度是通道数（1或2）
            if waveform.shape[0] > 2:
                waveform = waveform[:2]  # 只保留前两个通道
                print(f"[Suno生成器] 限制通道数: {waveform.shape}")
            
            # 如果是立体声，转换为单声道以避免复杂性
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                print(f"[Suno生成器] 转为单声道: {waveform.shape}")
            
            # 关键修复：转换为3D张量 [batch, channels, samples]
            waveform = waveform.unsqueeze(0)  # 添加batch维度
            print(f"[Suno生成器] 转换为3D张量 [batch, channels, samples]: {waveform.shape}")
            
            # 确保数据类型为float32
            waveform = waveform.float()
            
            # 确保张量是连续的
            if not waveform.is_contiguous():
                waveform = waveform.contiguous()
                print(f"[Suno生成器] 强制连续化")
            
            # 根据max_duration参数计算最大采样点数
            max_length = int(sample_rate * max_duration_seconds)  # 将秒转换为采样点数
            if waveform.shape[2] > max_length:  # 现在是3D，样本在第2维
                waveform = waveform[:, :, :max_length]
                print(f"[Suno生成器] 音频太长，已裁剪到 {max_length} 采样点 ({max_duration_seconds}秒)")
            
            # 最终验证：确保是3D张量
            assert len(waveform.shape) == 3, f"波形必须是3D张量，当前形状: {waveform.shape}"
            assert waveform.shape[0] >= 1, f"batch数必须>=1，当前: {waveform.shape[0]}"
            assert waveform.shape[1] >= 1, f"通道数必须>=1，当前: {waveform.shape[1]}"
            assert waveform.shape[2] >= 1, f"样本数必须>=1，当前: {waveform.shape[2]}"
            
            # 创建音频对象 - 只包含必需的字段
            audio_obj = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            
            print(f"[Suno生成器] 音频对象创建成功，最终波形形状: {waveform.shape}")
            return audio_obj
            
        except Exception as e:
            print(f"!!! [Suno生成器] 使用torchaudio加载音频失败: {e}")
            # 创建一个安全的空音频对象
            waveform = torch.zeros((1, 1, 16000), dtype=torch.float32)  # 确保3D [batch, channels, samples]
            sample_rate = 16000
            return {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
        
    except Exception as e:
        print(f"!!! [Suno生成器] 加载音频文件时出错: {e}")
        # 返回安全的空音频对象
        waveform = torch.zeros((1, 1, 16000), dtype=torch.float32)  # 确保3D [batch, channels, samples]
        sample_rate = 16000
        return {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
    finally:
        # 尝试删除临时文件
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass

class SunoGeneratorNode:
    """Suno文生歌高级生成器"""
    @classmethod
    def IS_CHANGED(s, **kwargs): return time.time()
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("API_KEY",),
                "base_url": ("BASE_URL",),
                "model_name": ("MODEL_NAME",),
                "title": ("STRING", {"default": ""}),
                "description_prompt": ("STRING", {"multiline": True, "placeholder": "输入详细的歌曲描述"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "make_instrumental": ("BOOLEAN", {"default": False}),
                "max_duration": ("INT", {"default": 20, "min": 10, "max": 180, "step": 5}),
            },
            "optional": {
                "lyrics": ("STRING", {"multiline": True, "default": "", "placeholder": "可选：直接输入歌词"}),
                "tags": ("STRING", {"default": "", "placeholder": "可选：音乐标签，如流行、摇滚、欢快、忧伤等，多个标签用逗号分隔"}),
                "timeout": ("INT", {"default": 300, "min": 30, "max": 600}),
                "max_attempts": ("INT", {"default": 30, "min": 1, "max": 50}),
                "retry_delay": ("FLOAT", {"default": 5.0, "min": 1.0, "max": 60.0, "step": 0.5}),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio1", "audio2", "audio_url1", "audio_url2", "prompt", "task_id", "response", "clip_id", "title")
    FUNCTION = "generate_music"
    CATEGORY = "AFA/音乐"

    def generate_music(self, api_key, base_url, model_name, title, description_prompt, seed=0, 
                       make_instrumental=False, max_duration=20, lyrics="", tags="", 
                       timeout=300, max_attempts=30, retry_delay=5.0):
        """生成音乐"""
        if not api_key:
            error_message = "API密钥不能为空"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        # 使用配置系统中的model_name，这已经是正确的mv值
        mv = model_name
        
        try:
            # 构建完整的提示词
            full_prompt = description_prompt
            
            # 如果有歌词，添加到提示中
            if lyrics:
                full_prompt = f"{full_prompt}\n\n歌词:\n{lyrics}"
                
            # 如果有标签，添加到提示中
            if tags:
                full_prompt = f"{full_prompt}\n\n标签: {tags}"
            
            # 根据API文档使用正确的参数格式
            payload = {
                "gpt_description_prompt": full_prompt,  # 使用gpt_description_prompt
                "make_instrumental": make_instrumental,
                "mv": mv,
            }
            
            # 添加可选参数
            if title:
                payload["title"] = title
            if tags:
                payload["tags"] = tags

            if seed > 0:
                payload["seed"] = seed
            
            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(10)
            
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            # 发送生成请求 - 根据API文档使用正确端点
            response = requests.post(
                f"{base_url}/suno/generate",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            pbar.update_absolute(20)
            
            if response.status_code != 200:
                error_message = f"API错误: {response.status_code} - {response.text}"
                print(f"!!! [Suno生成器] {error_message}")
                empty_audio = create_audio_object("")
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
                
            result = response.json()
            print(f"[Suno生成器] API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 根据API文档，/suno/generate 应该返回包含clips的响应
            # 可能的响应格式：
            # 1. {"id": "xxx", "clips": [...]}  - 标准格式
            # 2. {"code": "success", "data": {"clips": [...]}} - t8封装格式
            
            clips = []
            task_id = ""
            
            # 检查是否是t8平台的封装格式
            if result.get("code") == "success" and "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    clips = data.get("clips", [])
                    task_id = data.get("id", "")
                elif isinstance(data, list):
                    clips = data
            else:
                # 标准格式
                clips = result.get("clips", [])
                task_id = result.get("id", "")
            
            print(f"[Suno生成器] 解析结果 - task_id: {task_id}, clips数量: {len(clips)}")
            
            # 获取clip IDs用于后续查询
            clip_ids = [clip.get("id", "") for clip in clips if clip.get("id")]
            
            if not clip_ids:
                error_message = "响应中没有clip IDs"
                print(f"!!! [Suno生成器] {error_message}")
                print(f"[Suno生成器] 完整响应: {json.dumps(result, ensure_ascii=False)}")
                empty_audio = create_audio_object("")
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message, "response": result}, ensure_ascii=False), "", "")
            
            print(f"[Suno生成器] 找到 {len(clip_ids)} 个clip IDs: {clip_ids}")
                
            pbar.update_absolute(30)
            attempts = 0
            final_clips = []
            generated_prompt = ""
            extracted_tags = ""
            generated_title = ""
            
            # 轮询检查生成状态
            while attempts < max_attempts and len(final_clips) < 2:
                time.sleep(retry_delay)
                attempts += 1
                
                try:
                    # 根据API文档，使用feed API查询clips状态
                    clip_response = requests.get(
                        f"{base_url}/suno/feed/{','.join(clip_ids)}",
                        headers=headers,
                        timeout=timeout
                    )
                    
                    if clip_response.status_code != 200:
                        continue
                        
                    clips_data = clip_response.json()
                    
                    progress = min(80, 30 + (attempts * 50 // max_attempts))
                    pbar.update_absolute(progress)
                    
                    # 根据API文档，/suno/feed 返回clips数组
                    current_clips = []
                    
                    if isinstance(clips_data, list):
                        # 标准格式：直接返回clips数组
                        current_clips = clips_data
                        print(f"[Suno生成器] 轮询 {attempts}: 收到 {len(current_clips)} 个clips")
                    elif isinstance(clips_data, dict):
                        # t8封装格式
                        if clips_data.get("code") == "success":
                            data = clips_data.get("data", [])
                            if isinstance(data, list):
                                current_clips = data
                            elif isinstance(data, dict) and "clips" in data:
                                current_clips = data["clips"]
                        print(f"[Suno生成器] 轮询 {attempts}: 解析得到 {len(current_clips)} 个clips")
                    
                    # 找出已完成的clips
                    complete_clips = []
                    for clip in current_clips:
                        if not isinstance(clip, dict):
                            continue
                        
                        clip_status = clip.get("status", "").lower()
                        audio_url = (clip.get("audio_url") or 
                                   clip.get("audioUrl") or 
                                   clip.get("url") or 
                                   clip.get("mp3_url") or 
                                   clip.get("audio"))
                        
                        print(f"[Suno生成器] Clip {clip.get('id', 'unknown')}: status={clip_status}, has_url={bool(audio_url)}")
                        
                        # 检查clip是否完成
                        if clip_status in ["complete", "completed", "streaming"]:
                            if audio_url:
                                complete_clips.append(clip)
                                print(f"[Suno生成器] ✓ Clip完成: {clip.get('id')}, URL: {audio_url}")
                        elif clip_status in ["error", "failed"]:
                            print(f"!!! [Suno生成器] Clip失败: {clip.get('id')}")
                    
                    for clip in complete_clips:
                        # 如果有clip_ids，检查是否匹配；否则直接添加
                        clip_id = clip.get("id", "")
                        should_add = False
                        
                        if clip_ids:
                            # 有特定的clip_ids要查找
                            should_add = clip_id in clip_ids
                        else:
                            # 没有特定clip_ids，添加所有完成的clips
                            should_add = True
                        
                        if should_add and clip not in final_clips:
                            final_clips.append(clip)
                            if not generated_prompt and "prompt" in clip:
                                generated_prompt = clip["prompt"]
                            if not extracted_tags and "tags" in clip:
                                extracted_tags = clip["tags"]
                            if not generated_title and "title" in clip and clip["title"]:
                                generated_title = clip["title"]
                    
                    if len(final_clips) >= 2:
                        break
                        
                except Exception as e:
                    print(f"!!! [Suno生成器] 检查clip状态时出错: {str(e)}")
            
            if len(final_clips) < 2:
                error_message = f"{max_attempts}次尝试后仅收到{len(final_clips)}个完整clip"
                print(f"!!! [Suno生成器] {error_message}")
                
                if not final_clips:
                    empty_audio = create_audio_object("")
                    return (empty_audio, empty_audio, "", "", "", task_id, json.dumps({"error": error_message}, ensure_ascii=False), "", "")
                else:
                    # 如果只有一个clip，复制它作为第二个
                    print(f"[Suno生成器] 只有1个clip，将复制作为第二个音频")
                    final_clips.append(final_clips[0])
            
            # 使用生成的标题或用户提供的标题
            final_title = generated_title if generated_title else title

            # 为每个clip设置标题
            for clip in final_clips:
                if "title" not in clip or not clip["title"]:
                    clip["title"] = final_title
                    
            audio_urls = []
            clip_id_values = []
            
            # 提取音频URL
            for clip in final_clips[:2]:
                audio_url = ""
                
                # 检查多种可能的音频URL字段
                audio_url = (clip.get("audio_url") or 
                           clip.get("audioUrl") or 
                           clip.get("url") or 
                           clip.get("mp3_url") or 
                           clip.get("audio") or "")
                
                # 如果没有直接的URL字段，尝试在整个clip对象中搜索URL
                if not audio_url:
                    clip_str = str(clip)
                    if "cdn1.suno.ai" in clip_str:
                        match = re.search(r'https://cdn1\.suno\.ai/[^"\']+\.mp3', clip_str)
                        if match:
                            audio_url = match.group(0)
                
                if audio_url:
                    print(f"[Suno生成器] 找到音频URL: {audio_url}")
                    audio_urls.append(audio_url)
                else:
                    print(f"[Suno生成器] 未在clip中找到音频URL: {json.dumps(clip, ensure_ascii=False)}")
                    audio_urls.append("")
                    
                clip_id_value = clip.get("id", "")
                if clip_id_value:
                    clip_id_values.append(clip_id_value)
                else:
                    clip_id_values.append("")
                
            # 确保有两个URL
            while len(audio_urls) < 2:
                audio_urls.append("")
                
            while len(clip_id_values) < 2:
                clip_id_values.append("")
            
            # 创建音频对象
            pbar.update_absolute(90)
            print("[Suno生成器] 下载并处理音频文件...")
            
            # 使用try-except分别处理每个音频，确保即使一个失败也不影响另一个
            audio_objects = []
            for i, url in enumerate(audio_urls[:2]):
                try:
                    audio_obj = create_audio_object(url, max_duration_seconds=max_duration)
                    # 验证音频对象
                    wf = audio_obj["waveform"]
                    assert len(wf.shape) == 3, f"音频{i+1}波形必须是3D，当前: {wf.shape}"
                    print(f"[Suno生成器] 音频{i+1}对象验证通过: {wf.shape}")
                    audio_objects.append(audio_obj)
                except Exception as e:
                    print(f"!!! [Suno生成器] 创建音频对象{i+1}失败: {e}")
                    # 创建安全的空音频对象
                    sample_rate = 16000
                    waveform = torch.zeros((1, 1, int(sample_rate * max_duration)), dtype=torch.float32)  # 3D [batch, channels, samples]
                    audio_objects.append({
                        "waveform": waveform,
                        "sample_rate": sample_rate
                    })
            
            # 确保有两个音频对象
            while len(audio_objects) < 2:
                sample_rate = 16000
                waveform = torch.zeros((1, 1, int(sample_rate * max_duration)), dtype=torch.float32)  # 3D [batch, channels, samples]
                audio_objects.append({
                    "waveform": waveform,
                    "sample_rate": sample_rate
                })
            
            pbar.update_absolute(100)
            
            response_info = {
                "status": "success",
                "prompt": generated_prompt,
                "title": final_title, 
                "model": mv,
                "seed": seed if seed > 0 else "auto",
                "make_instrumental": make_instrumental,
                "clips_generated": len(final_clips),
                "tags": extracted_tags
            }

            return (
                audio_objects[0],
                audio_objects[1],
                audio_urls[0],
                audio_urls[1],
                generated_prompt,
                task_id,
                json.dumps(response_info, ensure_ascii=False),
                clip_id_values[0],
                final_title
            )
                
        except Exception as e:
            error_message = f"生成音乐时出错: {str(e)}"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")




# 导出节点类
NODE_CLASS_MAPPINGS = {
    "SunoGenerator": SunoGeneratorNode,
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "SunoGenerator": "Suno音乐生成器",
}