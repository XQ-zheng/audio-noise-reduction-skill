# Audio Noise Reduction Skill — V1.0

**触发语句 / Trigger:** `audio noise reduction skill`

一个采用开放 [Agent Skills](https://agentskills.io) 格式的音频除杂技能。默认尝试保留主要或离麦克风较近的说话人，抑制环境噪声、背景聊天和重叠人声；尽量保护原始音高、音色、音量与时间轴。依靠本地 Python 和模型运行，不绑定某一智能体或聊天模型。

**不能保证：** 完全去除重叠人声的同时，目标人声的音高、频谱、分贝绝对零变化。禁止自动调音、变速、响度归一化和 TTS 重建，处理后报告实际变化。WAV 无损保存不代表分离过程无损。

Portable Agent Skills instructions and local Python helpers for audio denoising and target speaker extraction. The default target is the foreground/main speaker. No intentional pitch shifting, time stretching, automatic gain normalization, or voice synthesis. Perfect separation with mathematically unchanged speech cannot be guaranteed.

## 各智能体安装路径

`~` 代表用户目录；Windows 通常为 `%USERPROFILE%`，例如 `C:\Users\你的用户名`。复制完整仓库，确保目标目录直接包含 `SKILL.md`，而不是再嵌套一层同名目录。

| 智能体 / 宿主 | 用户级目录 | 项目级目录 | 调用方式 |
|---|---|---|---|
| Codex | `~/.codex/skills/audio-noise-reduction-skill/`，设置 `CODEX_HOME` 时为 `$CODEX_HOME/skills/audio-noise-reduction-skill/` | `<项目>/.agents/skills/audio-noise-reduction-skill/` | `$audio-noise-reduction-skill` 或统一触发语句 |
| Claude Code | `~/.claude/skills/audio-noise-reduction-skill/` | `<项目>/.claude/skills/audio-noise-reduction-skill/` | `/audio-noise-reduction-skill` 或统一触发语句 |
| WorkBuddy | `~/.agents/skills/audio-noise-reduction-skill/` **作为安装源目录** | `<项目>/.agents/skills/audio-noise-reduction-skill/` **作为安装源目录** | 通过“技能 → 添加技能 → 上传技能”导入 Release ZIP、启用后输入统一触发语句 |
| DeepSeek，运行于 OpenCode | `~/.config/opencode/skills/audio-noise-reduction-skill/` | `<项目>/.opencode/skills/audio-noise-reduction-skill/` | 配置 DeepSeek 提供商，输入统一触发语句，让宿主加载技能 |
| 其他支持 Agent Skills 的智能体 | 按宿主文档设置；常见为 `~/.agents/skills/audio-noise-reduction-skill/` | 常见为 `<项目>/.agents/skills/audio-noise-reduction-skill/` | 使用宿主的技能加载功能 |

WorkBuddy 的官方文档确认支持上传本地技能包及从 `.agents` 等目录复制安装；上述路径是可控的安装源目录，**不声称是所有版本自动扫描或管理技能的内部目录**。最可靠的方式是导入 Release 附件 `audio-noise-reduction-skill-V1.0.zip`。无需创建未经官方确认的 `.workbuddy/skills`。

DeepSeek 是模型/服务名称，本身没有统一的本地技能目录。这里给出的是 **OpenCode + DeepSeek** 的具体路径。DeepSeek 网页聊天不能仅凭复制文件安装本地执行技能；其他 DeepSeek 宿主需按其自身的技能目录安装。

### 固定到 V1.0 安装

选择一个宿主安装，不必重复安装到所有路径。目录已存在时请停止并先检查，不覆盖自己的修改。

```bash
# Codex，未设置 CODEX_HOME 的常见情况
git clone --branch V1.0 --depth 1 https://github.com/XQ-zheng/audio-noise-reduction-skill.git ~/.codex/skills/audio-noise-reduction-skill

# Claude Code
git clone --branch V1.0 --depth 1 https://github.com/XQ-zheng/audio-noise-reduction-skill.git ~/.claude/skills/audio-noise-reduction-skill

# WorkBuddy：先获取技能源，再导入 Release ZIP 并启用
git clone --branch V1.0 --depth 1 https://github.com/XQ-zheng/audio-noise-reduction-skill.git ~/.agents/skills/audio-noise-reduction-skill

# OpenCode + DeepSeek
git clone --branch V1.0 --depth 1 https://github.com/XQ-zheng/audio-noise-reduction-skill.git ~/.config/opencode/skills/audio-noise-reduction-skill
```

Windows PowerShell 示例：

```powershell
git clone --branch V1.0 --depth 1 https://github.com/XQ-zheng/audio-noise-reduction-skill.git "$env:USERPROFILE/.claude/skills/audio-noise-reduction-skill"
```

安装后在宿主中新建会话或刷新技能列表；WorkBuddy 还需完成导入与启用。不同宿主的显式技能标识不支持空格，所以标准名称为 `audio-noise-reduction-skill`；统一的自然语言触发语句仍是 **`audio noise reduction skill`**。

## 终端命令：audio noise reduction skill

仓库同时提供真实的终端命令。先在仓库根目录建立并激活独立虚拟环境，再安装本地包；这只安装基础工具，不自动下载音频模型。

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell 改为：.venv/Scripts/Activate.ps1
python -m pip install .
audio noise reduction skill --help
```

若 PowerShell 执行策略不允许激活，直接用 `.venv/Scripts/python -m pip install .` 安装，然后用 `.venv/Scripts/audio.exe noise reduction skill --help`；不要求修改全局执行策略。激活环境后，命令即为 `audio noise reduction skill`。

```bash
# SAM：时间锚点必须替换为该录音中目标独自说话的真实区间
audio noise reduction skill input.wav preview.wav --backend sam --anchor 3.2:7.5 --description "foreground person speaking"

# 只有环境噪声时使用 ClearVoice；不是其他说话人的可靠分离器
audio noise reduction skill input.wav preview.wav --backend clearvoice

# 仅验证声音变化，不修改音频
python scripts/audio_tools.py input.wav preview.wav --solo-target 3.2:7.5 --report review.json
```

也可不安装 CLI，直接执行 `python scripts/audio_command.py noise reduction skill --help`。

## 模型与资源

- Python 3.11+；基础依赖为 numpy、scipy、soundfile。
- 音高检查：`python -m pip install ".[pitch]"`，再为检查脚本添加 `--pitch`。
- 环境噪声：`python -m pip install ".[clearvoice]"`，首次使用可能下载 `MossFormer2_SE_48K` 权重。
- 背景/重叠人声：按 [后端说明](references/backends.md) 安装 SAM Audio，取得 Hugging Face 权重访问许可并在本地登录。建议有足够显存的 CUDA GPU；脚本不自动回退到 CPU。
- 模型、权重和依赖各遵守其自身许可证，未随本仓库分发，不自动接受其许可。技能本身不将录音上传在线演示站。
- 默认保守强度 `--strength 0.8`；降低强度减少损伤，也会保留更多干扰。必须确认分析声道包含目标。
- 当前处理脚本用于单个可放入内存的片段，没有自动长音频分块。工作流见 [SKILL.md](SKILL.md)；验证细节见 [保真验证](references/verification.md)。

## 验证与已知限制

```bash
python -m unittest discover -s tests -v
```

V1.0 验证基础测量、掩膜、原文件保护和命令入口。合成信号测试不等于真人效果测试；本次发行未运行大型模型或验证真实录音，F0 依赖和 GPU/权重需使用者配置。不承诺所有宿主的每个版本都已端到端验证。

## 安装依据

- [Claude Code Skills](https://code.claude.com/docs/en/skills)：用户级和项目级 `.claude/skills`、显式 `/skill-name`。
- [WorkBuddy 技能](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)：上传本地技能包、启用技能、从 `.agents` 等目录复制。
- [OpenCode Agent Skills](https://opencode.ai/docs/skills/)：`.opencode/skills`、`~/.config/opencode/skills` 及 Claude/Agent 兼容目录。
- [Codex Skills](https://developers.openai.com/codex/skills/)；本项目的 `.codex/skills` 安装路径亦在作者本机 Codex 桌面环境验证。其他发行版可使用其文档规定的 `.agents/skills` 或 `CODEX_HOME` 路径。

## 开源许可

本项目脚本和文档使用 [MIT License](LICENSE)。模型权重不包含在 Release 中。
