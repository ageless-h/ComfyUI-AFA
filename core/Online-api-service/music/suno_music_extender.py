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

class SunoMusicExtender:
    """Suno 音乐续写器 - 专门用于扩展现有音乐"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API密钥": ("API_KEY",),
                "基础URL": ("BASE_URL",),
                "模型名称": ("MODEL_NAME",),
                "前任务ID": ("STRING", {"placeholder": "要续写的原始任务ID（必填）"}),
            },
            "optional": {
                # 音频输入相关
                "参考音频": ("AUDIO", {"tooltip": "用于续写的参考音频（推荐使用）"}),
                "续写起点": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 300.0, "step": 0.1, "tooltip": "从音频的第几秒开始继续创作\n0.0表示从头开始，可以设置具体的时间点"}),
                
                # 内容描述（按照用户要求的顺序：描述、歌词、风格）
                "续写提示词": ("STRING", {"default": "", "placeholder": "描述续写音乐的风格、情感、节奏等特征\n例如：轻快的流行音乐，带有电子元素", "multiline": True}),
                "歌词内容": ("STRING", {"multiline": True, "default": "", "placeholder": "续写部分的歌词内容\n可以是完整的歌词或歌词片段"}),
                "风格标签": ("STRING", {"default": "", "placeholder": "音乐风格标签，多个标签用逗号分隔\n例如：pop, electronic, upbeat, dance"}),
                
                # 基础设置
                "纯音乐模式": ("BOOLEAN", {"default": False, "tooltip": "生成纯音乐（无人声）"}),
                "声音性别": (["自动", "女声", "男声"], {"default": "自动", "tooltip": "选择人声性别"}),
                "最大时长": ("INT", {"default": 0, "min": 0, "max": 600, "step": 5, "tooltip": "最大音频长度（秒），设置为0表示不限制长度"}),
                
                # 高级选项
                "创意程度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "音乐创意和随机性程度"}),
                "风格权重": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "风格影响强度"}),
                "随机种子": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "随机种子，相同种子产生相似结果"}),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("续写音频1", "续写音频2", "音频链接1", "音频链接2", "续写信息", "任务ID", "响应信息", "片段ID", "歌曲标题")
    FUNCTION = "extend_music"
    CATEGORY = "AFA/音乐"

    def extend_music(self, **kwargs):
        # 参数映射
        api_key = kwargs.get("API密钥", "")
        base_url = kwargs.get("基础URL", "")
        model_name = kwargs.get("模型名称", "")
        task_id = kwargs.get("前任务ID", "")
        reference_audio = kwargs.get("参考音频", None)
        reference_audio_url = ""  # 已删除参考音频URL字段
        continue_clip_id = ""  # 已删除续写歌曲ID字段
        continue_at = kwargs.get("续写起点", 0.0)
        continued_aligned_prompt = kwargs.get("续写提示词", "")
        lyrics = kwargs.get("歌词内容", "")
        style_tags = kwargs.get("风格标签", "")
        make_instrumental = kwargs.get("纯音乐模式", False)
        vocal_gender_map = {"自动": "auto", "女声": "female", "男声": "male"}
        vocal_gender = vocal_gender_map.get(kwargs.get("声音性别", "自动"), "auto")
        max_duration = kwargs.get("最大时长", 120)
        weirdness_constraint = kwargs.get("创意程度", 0.5)
        style_weight = kwargs.get("风格权重", 0.5)
        seed = kwargs.get("随机种子", 0)
        
        # 固定参数
        task_type = "extend"
        custom_mode = True
        generation_type = "TEXT"
        timeout = 300
        max_attempts = 120
        retry_delay = 5.0
        
        """续写音乐"""
        if not api_key:
            error_message = "API密钥不能为空"
            print(f"!!! [Suno音乐续写器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        if not task_id:
            error_message = "续写扩展模式下前任务ID不能为空"
            print(f"!!! [Suno音乐续写器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        # 处理音频输入
        if reference_audio is not None:
            try:
                print(">>> [Suno音乐续写器] 检测到音频输入，正在处理...")
                # TODO: 实现音频上传功能
                # reference_audio_url = self.upload_audio_to_suno(reference_audio, api_key, base_url)
            except Exception as e:
                print(f"!!! [Suno音乐续写器] 音频处理失败: {str(e)}")
                reference_audio_url = ""
        
        # 直接使用选择器传入的模型名称
        mv = model_name
        
        try:
            # 根据模型版本确定字符限制
            is_v45_plus = any(v in mv.lower() for v in ['v4.5', 'v4_5', 'v5', 'chirp-v4-5', 'chirp-v5'])
            max_lyrics_chars = 5000 if is_v45_plus else 3000
            max_style_chars = 1000 if is_v45_plus else 200
            
            # 字符长度验证和截断
            if len(lyrics) > max_lyrics_chars:
                lyrics = lyrics[:max_lyrics_chars]
                print(f">>> [Suno音乐续写器] 歌词过长，已截断至{max_lyrics_chars}字符")
            
            if len(style_tags) > max_style_chars:
                style_tags = style_tags[:max_style_chars]
                print(f">>> [Suno音乐续写器] 风格标签过长，已截断至{max_style_chars}字符")
            
            # 构建续写请求数据
            data = {
                "custom_mode": custom_mode,
                "mv": mv,
                "input": {
                    "task_id": task_id,
                    "continue_at": continue_at,
                    "continue_clip_id": continue_clip_id,
                    "continued_aligned_prompt": continued_aligned_prompt,
                    "make_instrumental": make_instrumental,
                    "mv": mv,
                    "prompt": lyrics,
                    "tags": style_tags,
                    "type": generation_type,
                    "style_weight": style_weight,
                    "weirdness_constraint": weirdness_constraint,
                    "vocal_gender": vocal_gender
                }
            }
            
            if reference_audio_url:
                data["input"]["reference_audio_url"] = reference_audio_url
            
            if seed > 0:
                data["input"]["seed"] = seed
            
            if max_duration > 0:
                data["input"]["max_duration"] = max_duration
            
            print(f">>> [Suno音乐续写器] 开始续写音乐...")
            print(f">>> [Suno音乐续写器] 模型: {mv}")
            print(f">>> [Suno音乐续写器] 前任务ID: {task_id}")
            print(f">>> [Suno音乐续写器] 续写起点: {continue_at}秒")
            
            # 发送续写请求
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Connection': 'close'
            }
            
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            if response.status_code != 200:
                error_message = f"API请求失败: {response.status_code} - {response.text}"
                print(f"!!! [Suno音乐续写器] {error_message}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
            
            result = response.json()
            print(f"[Suno音乐续写器] API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 根据API文档，/suno/generate 应该返回包含clips的响应
            clips = []
            new_task_id = ""
            
            # 检查是否是t8平台的封装格式
            if result.get("code") == "success" and "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    clips = data.get("clips", [])
                    new_task_id = data.get("id", "")
                elif isinstance(data, list):
                    clips = data
            else:
                # 标准格式
                clips = result.get("clips", [])
                new_task_id = result.get("id", "")
            
            print(f"[Suno音乐续写器] 解析结果 - new_task_id: {new_task_id}, clips数量: {len(clips)}")
            
            # 获取clip IDs用于后续查询
            clip_ids = [clip.get("id", "") for clip in clips if clip.get("id")]
            
            if not clip_ids:
                error_message = "响应中没有clip IDs"
                print(f"!!! [Suno音乐续写器] {error_message}")
                print(f"[Suno音乐续写器] 完整响应: {json.dumps(result, ensure_ascii=False)}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message, "response": result}, ensure_ascii=False), "", "")
            print(f">>> [Suno音乐续写器] 新任务ID: {new_task_id}")
            
            # 轮询检查生成状态
            attempts = 0
            final_clips = []
            
            while attempts < max_attempts:
                attempts += 1
                print(f">>> [Suno音乐续写器] 检查续写状态 ({attempts}/{max_attempts})...")
                
                try:
                    # 查询任务状态
                    query_data = {
                        "custom_mode": True,
                        "mv": mv,
                        "input": {
                            "action": "get_feed",
                            "ids": new_task_id
                        }
                    }
                    
                    # 使用正确的 Suno API 端点查询状态
                    query_session = requests.Session()
                    query_headers = headers.copy()
                    query_headers["Connection"] = "close"
                    query_session.headers.update(query_headers)
                    
                    try:
                        clip_response = query_session.get(
                            f"{base_url}/suno/feed/{','.join(clip_ids)}",
                            timeout=timeout
                        )
                    except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                        print(f"[Suno音乐续写器] 状态查询连接错误 (尝试 {attempts}): {e}")
                        query_session.close()
                        continue
                    finally:
                        query_session.close()
                    
                    if clip_response.status_code != 200:
                        continue
                        
                    clips_data = clip_response.json()
                    
                    # 解析响应
                    current_clips = []
                    if isinstance(clips_data, list):
                        current_clips = clips_data
                        print(f"[Suno音乐续写器] 轮询 {attempts}: 收到 {len(current_clips)} 个clips")
                    elif isinstance(clips_data, dict):
                        if clips_data.get("code") == "success":
                            data = clips_data.get("data", [])
                            if isinstance(data, list):
                                current_clips = data
                            elif isinstance(data, dict) and "clips" in data:
                                current_clips = data["clips"]
                        print(f"[Suno音乐续写器] 轮询 {attempts}: 解析得到 {len(current_clips)} 个clips")
                    
                    # 找出已完成的clips
                    complete_clips = []
                    for clip in current_clips:
                        if not isinstance(clip, dict):
                            continue
                        
                        clip_status = clip.get("status", "").lower()
                        audio_url = (clip.get("audio_url") or 
                                   clip.get("audio") or 
                                   clip.get("url", "")).strip()
                        
                        print(f"[Suno音乐续写器] Clip {clip.get('id', 'unknown')}: 状态={clip_status}, 音频URL={'有' if audio_url else '无'}")
                        
                        if clip_status in ["complete", "completed"] and audio_url:
                            complete_clips.append(clip)
                        elif clip_status in ["streaming", "running", "processing"]:
                            print(f"[Suno音乐续写器] Clip {clip.get('id', 'unknown')} 仍在生成中...")
                    
                    if len(complete_clips) >= 2:
                        final_clips = complete_clips[:2]
                        print(f"[Suno音乐续写器] 续写完成！获得 {len(final_clips)} 个音频片段")
                        break
                    elif complete_clips:
                        print(f"[Suno音乐续写器] 已完成 {len(complete_clips)} 个片段，等待更多...")
                    else:
                        print(f"[Suno音乐续写器] 所有片段仍在生成中，继续等待...")
                    
                except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                    if "10054" in str(e):
                        print(f">>> [Suno音乐续写器] 连接被重置（Windows常见问题），继续等待...")
                    else:
                        print(f">>> [Suno音乐续写器] 连接错误: {str(e)}")
                except Exception as e:
                    print(f">>> [Suno音乐续写器] 状态查询异常: {str(e)}")
                
                if attempts < max_attempts:
                    time.sleep(retry_delay)
            
            if not final_clips:
                error_message = f"续写超时，已等待 {max_attempts * retry_delay} 秒"
                print(f"!!! [Suno音乐续写器] {error_message}")
                empty_audio = create_audio_object("", max_duration_seconds=max_duration)
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
            
            # 处理续写结果
            audio1 = create_audio_object("", max_duration_seconds=max_duration)
            audio2 = create_audio_object("", max_duration_seconds=max_duration)
            audio_url1 = ""
            audio_url2 = ""
            clip_id1 = ""
            clip_id2 = ""
            final_title = ""
            
            if len(final_clips) >= 1:
                clip1 = final_clips[0]
                audio_url1 = clip1.get('audio_url', '')
                clip_id1 = clip1.get('id', '')
                final_title = clip1.get('title', '')
                if audio_url1:
                    audio1 = create_audio_object(audio_url1, max_duration_seconds=max_duration)
                    print(f">>> [Suno音乐续写器] 续写音频1加载完成: {audio_url1}")
            
            if len(final_clips) >= 2:
                clip2 = final_clips[1]
                audio_url2 = clip2.get('audio_url', '')
                clip_id2 = clip2.get('id', '')
                if audio_url2:
                    audio2 = create_audio_object(audio_url2, max_duration_seconds=max_duration)
                    print(f">>> [Suno音乐续写器] 续写音频2加载完成: {audio_url2}")
            
            # 构建续写信息
            extend_info = f"原任务ID: {task_id}\n续写起点: {continue_at}秒\n风格: {style_tags}\n续写歌词: {lyrics[:100]}..." if len(lyrics) > 100 else f"原任务ID: {task_id}\n续写起点: {continue_at}秒\n风格: {style_tags}\n续写歌词: {lyrics}"
            
            # 构建响应信息
            response_info = {
                "original_task_id": task_id,
                "new_task_id": new_task_id,
                "continue_at": continue_at,
                "clips_count": len(final_clips),
                "model": mv,
                "status": "success"
            }
            
            clip_ids_str = f"{clip_id1},{clip_id2}" if clip_id2 else clip_id1
            
            print(f">>> [Suno音乐续写器] 续写完成！")
            return (audio1, audio2, audio_url1, audio_url2, extend_info, new_task_id, 
                   json.dumps(response_info, ensure_ascii=False), clip_ids_str, final_title)
            
        except Exception as e:
            error_message = f"续写过程中发生错误: {str(e)}"
            print(f"!!! [Suno音乐续写器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")

# 节点映射
NODE_CLASS_MAPPINGS = {
    "SunoMusicExtender": SunoMusicExtender
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SunoMusicExtender": "Suno音乐续写器"
}