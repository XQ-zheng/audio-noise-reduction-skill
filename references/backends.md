# 后端选择与运行

## 环境

基础工具需要 Python 3.11+、numpy、scipy、soundfile；F0 检查另需 librosa。在工作目录建独立虚拟环境，按任务需要安装；创建技能不需要下载大型权重。

```powershell
python -m venv work/audio-venv
work/audio-venv/Scripts/python -m pip install numpy scipy soundfile librosa
```

脚本输入为 soundfile 可解码的无损音频。MP3/M4A/视频先用 FFmpeg 解码，不改变采样率、声道、响度，例如 `ffmpeg -n -i recording.m4a -vn -c:a pcm_f32le work/input.wav`；不能恢复源文件已损失的信息。

## SAM Audio：目标说话人及背景人声

官方：[facebookresearch/sam-audio](https://github.com/facebookresearch/sam-audio)、[权重](https://huggingface.co/facebook/sam-audio-large)。接口依据官方 README 和 processor 源码，安装时记录实际 commit、权重 ID 和依赖版本。

- 官方接口：`SAMAudio.from_pretrained`、`SAMAudioProcessor.from_pretrained`、`processor(audios=[...], descriptions=[...], anchors=[[["+", start, end]]])`、`model.separate(..., predict_spans=False, reranking_candidates=1)`。
- 文字使用小写短语，如 `foreground person speaking`；锚点用目标独白区间。时间提示不保证说话人身份，要试听验证。
- 官方建议 CUDA GPU；检查显存。脚本默认 CUDA，不自动切到 CPU；`--device cpu` 是显式选择，模型仍可能不支持或很慢。
- 权重需 Hugging Face 授权和本地认证，引导用户在其终端完成，不索要或输出 token，不自动接受许可或绕过门禁。仅下载权重，录音在本地处理。
- 安装官方项目：`python -m pip install "git+https://github.com/facebookresearch/sam-audio.git"`。PyTorch/CUDA 采用官方对应平台方案，避免盲目替换已有安装。首次推理可能下载大型权重，先查磁盘空间和访问权限。
- 读取 `processor.audio_sampling_rate`，不猜采样率。源音频带宽超出模型时，脚本拒绝将其作为保真默认路线。输出掩膜投射到原始声道后仅是待验证试听版。
- 模型原生估计的样本数必须与其输入相同。长度变化时脚本停止，不猜测 padding 在尾部；确认官方实现的 padding 位置和延迟后，才另行作有记录的对齐处理。重采样的取整长度可裁去已知末端取整样本，不能因此裁掉模型真实内容。
- 脚本单次处理一个能放入内存的片段，没有自动分块。先试代表性的 15–30 秒；全长分块应带上下文、裁出中心结果、在重叠区平滑掩膜，每块验证目标身份。锚点须按各块时间重算。

## ClearVoice：只有环境噪声

官方：[ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio/tree/main/clearvoice)、[NumPy 接口](https://github.com/modelscope/ClearerVoice-Studio/blob/main/clearvoice/demo_Numpy2Numpy.py)。

安装 `python -m pip install clearvoice`；脚本调用 `ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])`，输入 `[batch, samples]` float32、48 kHz，返回 `[batch, samples]`；权重首次使用自动下载。

```powershell
python "<skill>/scripts/process_audio.py" input.wav noise-preview.wav --backend clearvoice --analysis-channel 0
```

这是环境降噪，不能保证删除其他说话人。不启用 `MossFormer2_SR_48K` 超分满足“不改变声音”。`MossFormer2_SS_16K` 两人分离限制带宽，不能默认替代全频段方案；`AV_MossFormer2_TSE_16K` 需要实际面部视频，不能虚构为音频声纹接口。

## 无合适后端

模型未授权、资源不足或目标不明确时，完成格式检查和目标/噪声区间分析，说明未完成的人声分离。用户明确接受妥协后，才提供低带宽分离、仅降噪或静音他人独立发言等替代，不能标为满足完整要求。
