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

def create_audio_object(url, max_duration_seconds=120):
    """创建音频对象 - 返回 ComfyUI 兼容的 3D 音频张量"""
    if not url:
        # 创建空音频 - 3D 格式 (batch, channels, samples)
        sample_rate = 44100
        duration = max_duration_seconds if max_duration_seconds > 0 else 2
        samples = int(sample_rate * duration)
        waveform = torch.zeros((1, 1, samples), dtype=torch.float32)  # 3D: (batch=1, channels=1, samples)
        return {"waveform": waveform, "sample_rate": sample_rate}
    
    try:
        response = requests.get(url, headers={'Connection': 'close'}, timeout=30)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            waveform, sample_rate = torchaudio.load(temp_file_path)
            
            # 确保音频是 2D 格式 (channels, samples)
            if len(waveform.shape) == 1:
                waveform = waveform.unsqueeze(0)  # 添加 channel 维度
            
            if max_duration_seconds > 0:
                max_samples = int(sample_rate * max_duration_seconds)
                if waveform.shape[1] > max_samples:
                    waveform = waveform[:, :max_samples]
            
            # 转换为 3D 格式 (batch, channels, samples) 以兼容 ComfyUI
            if len(waveform.shape) == 2:
                waveform = waveform.unsqueeze(0)  # 添加 batch 维度: (1, channels, samples)
            
            return {"waveform": waveform, "sample_rate": sample_rate}
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        print(f"!!! [音频加载错误] {str(e)}")
        sample_rate = 44100
        duration = max_duration_seconds if max_duration_seconds > 0 else 2
        samples = int(sample_rate * duration)
        waveform = torch.zeros((1, 1, samples), dtype=torch.float32)  # 3D: (batch=1, channels=1, samples)
        return {"waveform": waveform, "sample_rate": sample_rate}

class SunoMusicGenerator:
    """Suno 音乐生成器 - 专门用于创作新音乐"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API密钥": ("API_KEY",),
                "基础URL": ("BASE_URL",),
                "模型名称": ("MODEL_NAME",),
            },
            "optional": {
                # 基础信息
                "歌曲标题": ("STRING", {"default": "", "placeholder": "歌曲标题（最多80字符）\n例如：夏日回忆"}),
                
                # 内容描述（按照用户要求的顺序：描述、歌词、风格）
                "歌曲描述": ("STRING", {"multiline": True, "default": "", "placeholder": "描述歌曲的风格、情感、节奏等特征\n例如：一首轻快的夏日流行歌曲，带有清新的吉他旋律\n（非自定义模式下使用，最多500字符）"}),
                "歌词内容": ("STRING", {"multiline": True, "default": "", "placeholder": "完整的歌词内容\n自定义模式下V4.5+支持5000字符，V4及以下支持3000字符\n可以包含verse、chorus、bridge等结构"}),
                "风格标签": ("STRING", {"default": "", "placeholder": "音乐风格标签，多个标签用逗号分隔\n例如：pop, acoustic, summer, upbeat, guitar"}),
                
                # 模式设置
                "自定义模式": ("BOOLEAN", {"default": True, "tooltip": "启用自定义模式，支持完整歌词和风格控制"}),
                "纯音乐模式": ("BOOLEAN", {"default": False, "tooltip": "生成纯音乐（无人声）"}),
                "声音性别": (["自动", "女声", "男声"], {"default": "自动", "tooltip": "选择人声性别"}),
                "最大时长": ("INT", {"default": 0, "min": 0, "max": 600, "step": 5, "tooltip": "最大音频长度（秒），设置为0表示不限制长度"}),
                
                # 高级选项
                "创意程度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "音乐创意和随机性程度"}),
                "风格权重": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "风格影响强度"}),
                "排除风格": ("STRING", {"default": "", "placeholder": "要避免的音乐风格\n例如：heavy metal, rap"}),
                "随机种子": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "随机种子，相同种子产生相似结果"}),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("音频1", "音频2", "音频链接1", "音频链接2", "提示词", "任务ID", "响应信息", "片段ID", "歌曲标题")
    FUNCTION = "generate_music"
    CATEGORY = "AFA/音乐"

    def generate_music(self, **kwargs):
        # 参数映射
        api_key = kwargs.get("API密钥", "")
        base_url = kwargs.get("基础URL", "")
        model_name = kwargs.get("模型名称", "")
        title = kwargs.get("歌曲标题", "")
        lyrics = kwargs.get("歌词内容", "")
        style_tags = kwargs.get("风格标签", "")
        description_prompt = kwargs.get("歌曲描述", "")
        make_instrumental = kwargs.get("纯音乐模式", False)
        custom_mode = kwargs.get("自定义模式", True)
        vocal_gender_map = {"自动": "auto", "女声": "female", "男声": "male"}
        vocal_gender = vocal_gender_map.get(kwargs.get("声音性别", "自动"), "auto")
        max_duration = kwargs.get("最大时长", 120)
        weirdness_constraint = kwargs.get("创意程度", 0.7)
        style_weight = kwargs.get("风格权重", 0.5)
        negative_tags = kwargs.get("排除风格", "")
        seed = kwargs.get("随机种子", 0)
        
        # 固定参数
        task_type = "generate"
        generation_type = "TEXT"
        timeout = 300
        max_attempts = 120
        retry_delay = 5.0
        
        """生成音乐"""
        if not api_key:
            error_message = "API密钥不能为空"
            print(f"!!! [Suno音乐生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        # 直接使用选择器传入的模型名称
        mv = model_name
        
        try:
            # 根据模型版本确定字符限制
            is_v45_plus = any(v in mv.lower() for v in ['v4.5', 'v4_5', 'v5', 'chirp-v4-5', 'chirp-v5'])
            max_lyrics_chars = 5000 if is_v45_plus else 3000
            max_style_chars = 1000 if is_v45_plus else 200
            
            # 字符长度验证和截断
            if len(title) > 80:
                title = title[:80]
                print(f">>> [Suno音乐生成器] 标题过长，已截断至80字符")
            
            if len(lyrics) > max_lyrics_chars:
                lyrics = lyrics[:max_lyrics_chars]
                print(f">>> [Suno音乐生成器] 歌词过长，已截断至{max_lyrics_chars}字符")
            
            if len(style_tags) > max_style_chars:
                style_tags = style_tags[:max_style_chars]
                print(f">>> [Suno音乐生成器] 风格标签过长，已截断至{max_style_chars}字符")
            
            if len(description_prompt) > 500:
                description_prompt = description_prompt[:500]
                print(f">>> [Suno音乐生成器] 描述过长，已截断至500字符")
            
            # 构建请求数据 - 使用正确的 Suno API 格式
            payload = {
                "generation_type": generation_type,
                "mv": mv,
                "make_instrumental": make_instrumental
            }
            
            if custom_mode:
                # 自定义模式
                if title:
                    payload["title"] = title
                if style_tags:
                    payload["tags"] = style_tags
                if not make_instrumental and lyrics:
                    payload["prompt"] = lyrics
                if negative_tags:
                    payload["negative_tags"] = negative_tags
                if style_weight != 0.5:
                    payload["style_weight"] = style_weight
                if weirdness_constraint != 0.7:
                    payload["weirdness_constraint"] = weirdness_constraint
                if vocal_gender != "auto":
                    payload["vocal_gender"] = vocal_gender
            else:
                # 非自定义模式
                if description_prompt:
                    payload["gpt_description_prompt"] = description_prompt
            
            if seed > 0:
                payload["seed"] = seed
            
            if max_duration > 0:
                payload["max_duration"] = max_duration
            
            print(f">>> [Suno音乐生成器] 开始生成音乐...")
            print(f">>> [Suno音乐生成器] 模型: {mv}")
            print(f">>> [Suno音乐生成器] 标题: {title}")
            print(f">>> [Suno音乐生成器] 风格: {style_tags}")
            print(f">>> [Suno音乐生成器] 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            # 发送生成请求 - 使用正确的 Suno API 端点
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Connection': 'close'
            }
            
            api_url = f"{base_url}/suno/generate"
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                error_message = f"API请求失败: {response.status_code} - {response.text}"
                print(f"!!! [Suno音乐生成器] {error_message}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
            
            result = response.json()
            print(f"[Suno音乐生成器] API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
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
            
            print(f"[Suno音乐生成器] 解析结果 - task_id: {task_id}, clips数量: {len(clips)}")
            
            # 获取clip IDs用于后续查询
            clip_ids = [clip.get("id", "") for clip in clips if clip.get("id")]
            
            if not clip_ids:
                error_message = "响应中没有clip IDs"
                print(f"!!! [Suno音乐生成器] {error_message}")
                print(f"[Suno音乐生成器] 完整响应: {json.dumps(result, ensure_ascii=False)}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message, "response": result}, ensure_ascii=False), "", "")
            
            print(f"[Suno音乐生成器] 找到 {len(clip_ids)} 个clip IDs: {clip_ids}")
            
            # 轮询检查生成状态
            attempts = 0
            final_clips = []
            
            while attempts < max_attempts:
                attempts += 1
                print(f">>> [Suno音乐生成器] 检查生成状态 ({attempts}/{max_attempts})...")
                
                try:
                    # 根据API文档，使用feed API查询clips状态
                    # 使用会话管理和错误重试
                    query_session = requests.Session()
                    query_headers = headers.copy()
                    query_headers["Connection"] = "close"  # 明确关闭连接
                    query_session.headers.update(query_headers)
                    
                    try:
                        clip_response = query_session.get(
                            f"{base_url}/suno/feed/{','.join(clip_ids)}",
                            timeout=timeout
                        )
                    except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                        print(f"[Suno音乐生成器] 状态查询连接错误 (尝试 {attempts}): {e}")
                        query_session.close()
                        continue  # 跳过这次查询，等待下次重试
                    finally:
                        query_session.close()  # 确保会话被正确关闭
                    
                    if clip_response.status_code != 200:
                        continue
                        
                    clips_data = clip_response.json()
                    
                    # 根据API文档，/suno/feed 返回clips数组
                    current_clips = []
                    
                    if isinstance(clips_data, list):
                        # 标准格式：直接返回clips数组
                        current_clips = clips_data
                        print(f"[Suno音乐生成器] 轮询 {attempts}: 收到 {len(current_clips)} 个clips")
                    elif isinstance(clips_data, dict):
                        # t8封装格式
                        if clips_data.get("code") == "success":
                            data = clips_data.get("data", [])
                            if isinstance(data, list):
                                current_clips = data
                            elif isinstance(data, dict) and "clips" in data:
                                current_clips = data["clips"]
                        print(f"[Suno音乐生成器] 轮询 {attempts}: 解析得到 {len(current_clips)} 个clips")
                    
                    # 找出已完成的clips
                    complete_clips = []
                    for clip in current_clips:
                        if not isinstance(clip, dict):
                            continue
                        
                        clip_status = clip.get("status", "").lower()
                        audio_url = (clip.get("audio_url") or 
                                   clip.get("audio") or 
                                   clip.get("url", "")).strip()
                        
                        print(f"[Suno音乐生成器] Clip {clip.get('id', 'unknown')}: 状态={clip_status}, 音频URL={'有' if audio_url else '无'}")
                        
                        if clip_status in ["complete", "completed"] and audio_url:
                            complete_clips.append(clip)
                        elif clip_status in ["streaming", "running", "processing"]:
                            print(f"[Suno音乐生成器] Clip {clip.get('id', 'unknown')} 仍在生成中...")
                    
                    if len(complete_clips) >= 2:
                        final_clips = complete_clips[:2]
                        print(f"[Suno音乐生成器] 生成完成！获得 {len(final_clips)} 个音频片段")
                        break
                    elif complete_clips:
                        print(f"[Suno音乐生成器] 已完成 {len(complete_clips)} 个片段，等待更多...")
                    else:
                        print(f"[Suno音乐生成器] 所有片段仍在生成中，继续等待...")
                    
                except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                    if "10054" in str(e):
                        print(f">>> [Suno音乐生成器] 连接被重置（Windows常见问题），继续等待...")
                    else:
                        print(f">>> [Suno音乐生成器] 连接错误: {str(e)}")
                except Exception as e:
                    print(f">>> [Suno音乐生成器] 状态查询异常: {str(e)}")
                
                if attempts < max_attempts:
                    time.sleep(retry_delay)
            
            if not final_clips:
                error_message = f"生成超时，已等待 {max_attempts * retry_delay} 秒"
                print(f"!!! [Suno音乐生成器] {error_message}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
            
            # 处理生成结果
            audio1 = create_audio_object("", max_duration_seconds=max_duration)
            audio2 = create_audio_object("", max_duration_seconds=max_duration)
            audio_url1 = ""
            audio_url2 = ""
            clip_id1 = ""
            clip_id2 = ""
            final_title = title
            
            if len(final_clips) >= 1:
                clip1 = final_clips[0]
                audio_url1 = clip1.get('audio_url', '')
                clip_id1 = clip1.get('id', '')
                if not final_title:
                    final_title = clip1.get('title', '')
                if audio_url1:
                    audio1 = create_audio_object(audio_url1, max_duration_seconds=max_duration)
                    print(f">>> [Suno音乐生成器] 音频1加载完成: {audio_url1}")
            
            if len(final_clips) >= 2:
                clip2 = final_clips[1]
                audio_url2 = clip2.get('audio_url', '')
                clip_id2 = clip2.get('id', '')
                if audio_url2:
                    audio2 = create_audio_object(audio_url2, max_duration_seconds=max_duration)
                    print(f">>> [Suno音乐生成器] 音频2加载完成: {audio_url2}")
            
            # 构建提示词信息
            prompt_info = f"标题: {final_title}\n风格: {style_tags}\n歌词: {lyrics[:100]}..." if len(lyrics) > 100 else f"标题: {final_title}\n风格: {style_tags}\n歌词: {lyrics}"
            
            # 构建响应信息
            response_info = {
                "task_id": task_id,
                "clips_count": len(final_clips),
                "model": mv,
                "status": "success"
            }
            
            clip_ids_str = f"{clip_id1},{clip_id2}" if clip_id2 else clip_id1
            
            print(f">>> [Suno音乐生成器] 生成完成！")
            return (audio1, audio2, audio_url1, audio_url2, prompt_info, task_id, 
                   json.dumps(response_info, ensure_ascii=False), clip_ids_str, final_title)
            
        except Exception as e:
            error_message = f"生成过程中发生错误: {str(e)}"
            print(f"!!! [Suno音乐生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")

# 节点映射
NODE_CLASS_MAPPINGS = {
    "SunoMusicGenerator": SunoMusicGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SunoMusicGenerator": "Suno音乐生成器"
}