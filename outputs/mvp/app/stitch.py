"""ffmpeg 拼接：参数归一化 + 转场 + 音频混音。"""

DIMS = {
    "480p": (854, 480),
    "540p": (960, 540),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2K": (2560, 1440),
    "4K": (3840, 2160),
}


def normalize_args(resolution="1080p", fps=30):
    """统一分辨率/帧率/编码/像素格式，避免黑边、卡顿、音画不同步。"""
    w, h = DIMS.get(resolution, DIMS["1080p"])
    return {
        "width": w, "height": h, "fps": fps,
        "codec": "libx264", "pix_fmt": "yuv420p", "crf": 18, "preset": "medium",
    }


def normalize_command(clip, out, args):
    """把单个片段归一化（等比缩放 + 居中填充黑边 + 统一帧率/格式），去音轨。"""
    vf = (
        f"scale={args['width']}:{args['height']}:force_original_aspect_ratio=decrease,"
        f"pad={args['width']}:{args['height']}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={args['fps']},setsar=1,format={args['pix_fmt']}"
    )
    return [
        "ffmpeg", "-y", "-i", clip, "-vf", vf,
        "-c:v", args["codec"], "-crf", str(args["crf"]), "-preset", args["preset"],
        "-an", out,
    ]


def concat_command(list_path, out):
    """用 concat demuxer 硬切拼接（片段编码参数一致，由 normalize 保证）。"""
    return ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out]


def mix_bgm_command(video, bgm, out, volume=0.7):
    """把背景音乐混入成片：音量可调，短音乐循环。"""
    return [
        "ffmpeg", "-y", "-i", video, "-stream_loop", "-1", "-i", bgm,
        "-filter_complex",
        f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=3[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", out,
    ]


def fade_command(clips, output, args, clip_duration=30, fade_dur=0.5, mode="fade"):
    """用 xfade 做叠化/淡入淡出，返回一条 ffmpeg 命令。"""
    vf = (
        f"scale={args['width']}:{args['height']}:force_original_aspect_ratio=decrease,"
        f"pad={args['width']}:{args['height']}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={args['fps']},setsar=1,format={args['pix_fmt']}"
    )
    fc = [f"[{i}:v]{vf}[v{i}]" for i in range(len(clips))]
    last = "[v0]"
    offset = clip_duration - fade_dur
    acc = offset
    for i in range(1, len(clips)):
        out_label = f"[x{i}]"
        fc.append(f"{last}[v{i}]xfade=transition={mode}:duration={fade_dur}:offset={acc:.2f}{out_label}")
        last = out_label
        acc += offset
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    cmd += ["-filter_complex", ";".join(fc), "-map", last,
            "-c:v", args["codec"], "-crf", str(args["crf"]), "-preset", args["preset"], output]
    return cmd


def stitch(clips, output, resolution="1080p", fps=30, transition="硬切",
           bgm=None, bgm_volume=0.7, clip_duration=30):
    """返回按顺序执行的步骤列表（调用方决定是否真正执行）。"""
    args = normalize_args(resolution, fps)
    if transition in ("叠化", "淡入淡出") and len(clips) > 1:
        mode = "dissolve" if transition == "叠化" else "fade"
        steps = [{"type": "xfade", "cmd": fade_command(clips, output, args,
                                                       clip_duration=clip_duration, mode=mode),
                  "out": output}]
    else:
        steps = []
        norm = []
        for i, clip in enumerate(clips):
            tmp = f"{output}.norm{i}.mp4"
            steps.append({"type": "normalize", "cmd": normalize_command(clip, tmp, args), "out": tmp})
            norm.append(tmp)
        list_path = f"{output}.list"
        steps.append({"type": "write_list", "path": list_path, "files": norm})
        steps.append({"type": "concat", "cmd": concat_command(list_path, output), "out": output})
    if bgm:
        steps.append({"type": "bgm", "cmd": mix_bgm_command(output, bgm, output, bgm_volume)})
    return steps
