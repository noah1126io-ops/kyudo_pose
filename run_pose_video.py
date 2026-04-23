import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm

from mmpose.apis import MMPoseInferencer


COCO_KEYPOINTS = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run RTMPose/MMPose 2D pose estimation on a single-person video."
    )
    parser.add_argument("--input", required=True, help="Path to input video.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where pose video and keypoint files are saved.",
    )
    parser.add_argument(
        "--pose2d",
        default="human",
        help="MMPose pose2d alias or config name. Default: human",
    )
    parser.add_argument(
        "--device",
        default=None,
        help='Inference device, e.g. "cpu" or "cuda:0". Default: auto.',
    )
    parser.add_argument(
        "--kpt-thr",
        type=float,
        default=0.3,
        help="Visualization keypoint threshold. Default: 0.3",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=4,
        help="Keypoint radius for visualization. Default: 4",
    )
    parser.add_argument(
        "--thickness",
        type=int,
        default=2,
        help="Line thickness for visualization. Default: 2",
    )
    return parser.parse_args()


def select_best_instance(predictions):
    if isinstance(predictions, list) and len(predictions) == 1 and isinstance(
        predictions[0], list
    ):
        predictions = predictions[0]

    if not predictions:
        return None

    def score_of(instance):
        scores = np.asarray(instance.get("keypoint_scores", []), dtype=float)
        if scores.size == 0:
            return -np.inf
        return float(np.nanmean(scores))

    return max(predictions, key=score_of)


def build_frame_row(frame_idx, fps, keypoints, keypoint_scores):
    row = {
        "frame_index": frame_idx,
        "timestamp_sec": frame_idx / fps if fps > 0 else np.nan,
    }

    for idx, name in enumerate(COCO_KEYPOINTS):
        if idx < len(keypoints):
            row[f"{name}_x"] = float(keypoints[idx][0])
            row[f"{name}_y"] = float(keypoints[idx][1])
        else:
            row[f"{name}_x"] = np.nan
            row[f"{name}_y"] = np.nan

        if idx < len(keypoint_scores):
            row[f"{name}_score"] = float(keypoint_scores[idx])
        else:
            row[f"{name}_score"] = np.nan

    return row


def build_json_record(frame_idx, fps, keypoints, keypoint_scores):
    keypoint_dict = {}
    for idx, name in enumerate(COCO_KEYPOINTS):
        if idx < len(keypoints):
            xy = keypoints[idx]
            score = keypoint_scores[idx] if idx < len(keypoint_scores) else np.nan
            keypoint_dict[name] = {
                "x": float(xy[0]),
                "y": float(xy[1]),
                "score": float(score),
            }
        else:
            keypoint_dict[name] = {"x": None, "y": None, "score": None}

    return {
        "frame_index": frame_idx,
        "timestamp_sec": frame_idx / fps if fps > 0 else None,
        "keypoints": keypoint_dict,
    }


def ensure_bgr_uint8(image):
    vis = np.asarray(image)
    if vis.dtype != np.uint8:
        vis = np.clip(vis, 0, 255).astype(np.uint8)
    if vis.ndim == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
    return vis


def create_video_writer(video_out_path, fps, width, height):
    # Prefer codecs that are more likely to play in browser-based video tags.
    codec_candidates = ["avc1", "H264", "mp4v"]

    for codec_name in codec_candidates:
        fourcc = cv2.VideoWriter_fourcc(*codec_name)
        writer = cv2.VideoWriter(str(video_out_path), fourcc, fps, (width, height))
        if writer.isOpened():
            return writer, codec_name
        writer.release()

    raise RuntimeError(f"Could not open video writer: {video_out_path}")


def run_pose_video(
    input_path,
    output_dir,
    pose2d="human",
    device=None,
    kpt_thr=0.3,
    radius=4,
    thickness=2,
    progress_callback=None,
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_out_path = output_dir / "pose_overlay.mp4"
    csv_out_path = output_dir / "keypoints.csv"
    json_out_path = output_dir / "keypoints.json"

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer, video_codec = create_video_writer(video_out_path, fps, width, height)

    inferencer = MMPoseInferencer(
        pose2d=pose2d,
        det_model="whole_image",
        device=device,
    )

    rows = []
    json_records = []

    progress = None
    if progress_callback is None:
        progress = tqdm(
            total=frame_count if frame_count > 0 else None,
            desc="Pose inference",
            unit="frame",
        )

    frame_idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            result = next(
                inferencer(
                    frame,
                    return_vis=True,
                    draw_bbox=False,
                    radius=radius,
                    thickness=thickness,
                    kpt_thr=kpt_thr,
                    num_instances=1,
                )
            )

            predictions = result.get("predictions", [])
            best_instance = select_best_instance(predictions)

            if best_instance is None:
                keypoints = np.empty((0, 2), dtype=float)
                keypoint_scores = np.empty((0,), dtype=float)
            else:
                keypoints = np.asarray(best_instance.get("keypoints", []), dtype=float)
                keypoint_scores = np.asarray(
                    best_instance.get("keypoint_scores", []), dtype=float
                )

            rows.append(build_frame_row(frame_idx, fps, keypoints, keypoint_scores))
            json_records.append(
                build_json_record(frame_idx, fps, keypoints, keypoint_scores)
            )

            vis_list = result.get("visualization", [])
            if vis_list:
                vis_frame = ensure_bgr_uint8(vis_list[0])
                if vis_frame.shape[1] != width or vis_frame.shape[0] != height:
                    vis_frame = cv2.resize(vis_frame, (width, height))
            else:
                vis_frame = frame

            writer.write(vis_frame)

            frame_idx += 1
            if progress is not None:
                progress.update(1)
            if progress_callback is not None:
                progress_callback(frame_idx, frame_count)
    finally:
        if progress is not None:
            progress.close()
        cap.release()
        writer.release()

    df = pd.DataFrame(rows)
    df.to_csv(csv_out_path, index=False, encoding="utf-8")

    payload = {
        "meta": {
            "input_video": str(input_path),
            "output_video": str(video_out_path),
            "pose2d": pose2d,
            "device": device,
            "video_codec": video_codec,
            "fps": fps,
            "frame_width": width,
            "frame_height": height,
            "frame_count": frame_idx,
            "keypoint_format": "coco17",
            "det_model": "whole_image",
        },
        "frames": json_records,
    }
    with json_out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {
        "input_video": input_path,
        "output_dir": output_dir,
        "overlay_video": video_out_path,
        "csv_path": csv_out_path,
        "json_path": json_out_path,
        "fps": fps,
        "frame_width": width,
        "frame_height": height,
        "frame_count": frame_idx,
        "pose2d": pose2d,
        "device": device,
        "video_codec": video_codec,
    }


def main():
    args = parse_args()
    result = run_pose_video(
        input_path=args.input,
        output_dir=args.output_dir,
        pose2d=args.pose2d,
        device=args.device,
        kpt_thr=args.kpt_thr,
        radius=args.radius,
        thickness=args.thickness,
    )

    print(f"Saved overlay video: {result['overlay_video']}")
    print(f"Saved CSV: {result['csv_path']}")
    print(f"Saved JSON: {result['json_path']}")


if __name__ == "__main__":
    main()
