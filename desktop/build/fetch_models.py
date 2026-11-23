"""构建前准备 RTMPose 模型权重，并核对 SHA256。

模型不入库。CI 每次构建都从 OpenMMLab 官方地址下载，本机构建可以用
--from 指向一份已经下好的目录，省得重复下载。

live_api.py 里构造的是 RTMPoseModel(..., "detected")，之后才把 roi_mode 改成
locked；检测器实例在构造时就定下来了，所以本机路径真正用到的是 detector.onnx
（yolox_tiny），不是 detector_m.onnx。这里只准备真正用得到的两个文件。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VISION = REPO / "algorithm" / "rehab-pose-demo"
TARGET = VISION / "models" / "rtmpose"
NEEDED = ("pose.onnx", "detector.onnx")

# 官方压缩包里的 ONNX 文件在本机实测出来的摘要。校验的是解压后的权重本身，
# 不是压缩包，所以换一台机器下载也应当一致；对不上就不要继续构建。
EXPECTED_SHA256 = {
    "pose.onnx": "5c0a4bf67953e6d2ac43ce15e77dc9d5d354ae18430a47d2c5963a7bc5683e3c",
    "detector.onnx": "ceb11c07298f95c50d7c5abeb906d03340c85f23aa79e3e66966e7fb6c307250",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_digests() -> dict:
    """优先读同目录的 model-sha256.json，没有就用文件里写死的那份。"""
    path = Path(__file__).resolve().parent / "model-sha256.json"
    if path.is_file():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return dict(EXPECTED_SHA256)
        return {k: str(v) for k, v in document.items() if k in NEEDED}
    return dict(EXPECTED_SHA256)


def copy_from(source: Path) -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in NEEDED:
        origin = source / name
        if not origin.is_file():
            raise SystemExit("来源目录里没有 %s" % origin)
        if (TARGET / name).resolve() == origin.resolve():
            continue
        shutil.copy2(origin, TARGET / name)
        side = origin.with_suffix(".source.json")
        if side.is_file():
            shutil.copy2(side, TARGET / side.name)
        print("已复制 %s" % name)


def download() -> None:
    sys.path.insert(0, str(VISION))
    from rehab_pose.model import download_rtmpose
    # roi_mode="detected" 对应 live_api.py 的实际构造方式，只下这两个文件。
    download_rtmpose(TARGET, roi_mode="detected")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="准备 RTMPose 模型权重")
    parser.add_argument("--from", dest="source", default=None,
                        help="从已有目录复制，不联网下载")
    parser.add_argument("--write-digests", action="store_true",
                        help="把当前文件的 SHA256 写进 model-sha256.json，首次建立基准时用")
    args = parser.parse_args(argv)

    if args.source:
        copy_from(Path(args.source).expanduser().resolve())
    else:
        download()

    digests = {name: sha256_of(TARGET / name) for name in NEEDED}
    for name, value in digests.items():
        size = (TARGET / name).stat().st_size
        print("%s  %.1f MB  sha256=%s" % (name, size / 1048576, value))

    if args.write_digests:
        path = Path(__file__).resolve().parent / "model-sha256.json"
        path.write_text(json.dumps(digests, indent=2) + "\n", encoding="utf-8")
        print("已写入 %s" % path)
        return 0

    expected = expected_digests()
    problems = []
    for name in NEEDED:
        want = (expected.get(name) or "").strip()
        if not want:
            problems.append("%s 没有基准摘要，无法校验" % name)
        elif want != digests[name]:
            problems.append("%s 摘要不符：期望 %s，实际 %s" % (name, want, digests[name]))
    if problems:
        for line in problems:
            print("校验失败：" + line)
        return 1
    print("模型 SHA256 校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
