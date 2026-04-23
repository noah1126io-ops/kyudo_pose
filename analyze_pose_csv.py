import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze pose keypoint CSV and generate simple kyudo metrics."
    )
    parser.add_argument("--csv", required=True, help="Path to keypoints CSV.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where metrics.csv and plots are saved.",
    )
    parser.add_argument(
        "--score-thr",
        type=float,
        default=0.3,
        help="Minimum keypoint score required for analysis. Default: 0.3",
    )
    return parser.parse_args()


def get_point(row, name, score_thr):
    x = row.get(f"{name}_x", np.nan)
    y = row.get(f"{name}_y", np.nan)
    score = row.get(f"{name}_score", np.nan)
    if pd.isna(x) or pd.isna(y) or pd.isna(score) or score < score_thr:
        return None
    return np.array([float(x), float(y)], dtype=float)


def compute_angle(a, b, c):
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return np.nan
    cos_theta = np.dot(ba, bc) / (norm_ba * norm_bc)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_theta)))


def compute_torso_tilt(mid_shoulder, mid_hip):
    vector = mid_shoulder - mid_hip
    dx = vector[0]
    dy = vector[1]
    if dx == 0 and dy == 0:
        return np.nan
    return float(np.degrees(np.arctan2(dx, -dy)))


def analyze_keypoints_df(df, score_thr=0.3):
    metrics = []

    for _, row in df.iterrows():
        left_shoulder = get_point(row, "left_shoulder", score_thr)
        right_shoulder = get_point(row, "right_shoulder", score_thr)
        left_elbow = get_point(row, "left_elbow", score_thr)
        right_elbow = get_point(row, "right_elbow", score_thr)
        left_wrist = get_point(row, "left_wrist", score_thr)
        right_wrist = get_point(row, "right_wrist", score_thr)
        left_hip = get_point(row, "left_hip", score_thr)
        right_hip = get_point(row, "right_hip", score_thr)

        shoulder_height_diff = np.nan
        if left_shoulder is not None and right_shoulder is not None:
            shoulder_height_diff = float(left_shoulder[1] - right_shoulder[1])

        left_elbow_angle = np.nan
        if (
            left_shoulder is not None
            and left_elbow is not None
            and left_wrist is not None
        ):
            left_elbow_angle = compute_angle(left_shoulder, left_elbow, left_wrist)

        right_elbow_angle = np.nan
        if (
            right_shoulder is not None
            and right_elbow is not None
            and right_wrist is not None
        ):
            right_elbow_angle = compute_angle(right_shoulder, right_elbow, right_wrist)

        mid_shoulder = None
        if left_shoulder is not None and right_shoulder is not None:
            mid_shoulder = (left_shoulder + right_shoulder) / 2.0

        mid_hip = None
        if left_hip is not None and right_hip is not None:
            mid_hip = (left_hip + right_hip) / 2.0

        torso_tilt_deg = np.nan
        if mid_shoulder is not None and mid_hip is not None:
            torso_tilt_deg = compute_torso_tilt(mid_shoulder, mid_hip)

        metrics.append(
            {
                "frame_index": row["frame_index"],
                "timestamp_sec": row["timestamp_sec"],
                "shoulder_height_diff_px": shoulder_height_diff,
                "left_elbow_angle_deg": left_elbow_angle,
                "right_elbow_angle_deg": right_elbow_angle,
                "elbow_angle_diff_deg": np.nan
                if np.isnan(left_elbow_angle) or np.isnan(right_elbow_angle)
                else abs(left_elbow_angle - right_elbow_angle),
                "left_wrist_y_px": np.nan if left_wrist is None else float(left_wrist[1]),
                "right_wrist_y_px": np.nan if right_wrist is None else float(right_wrist[1]),
                "wrist_height_diff_px": np.nan
                if left_wrist is None or right_wrist is None
                else float(left_wrist[1] - right_wrist[1]),
                "torso_tilt_deg": torso_tilt_deg,
            }
        )

    return pd.DataFrame(metrics)


def save_plot(fig, output_path):
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_metrics(metrics_df, plots_dir):
    x = metrics_df["timestamp_sec"]

    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(x, metrics_df["shoulder_height_diff_px"], color="tab:blue")
    ax1.set_title("Shoulder Height Difference")
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel("left_shoulder_y - right_shoulder_y [px]")
    ax1.grid(True, alpha=0.3)
    save_plot(fig1, plots_dir / "shoulder_height_diff_px.png")

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(x, metrics_df["left_elbow_angle_deg"], label="Left elbow", color="tab:green")
    ax2.plot(
        x,
        metrics_df["right_elbow_angle_deg"],
        label="Right elbow",
        color="tab:orange",
    )
    ax2.set_title("Shoulder-Elbow-Wrist Angle")
    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel("Angle [deg]")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    save_plot(fig2, plots_dir / "elbow_angles_deg.png")

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.plot(x, metrics_df["left_wrist_y_px"], label="Left wrist", color="tab:red")
    ax3.plot(x, metrics_df["right_wrist_y_px"], label="Right wrist", color="tab:purple")
    ax3.set_title("Wrist Height Time Series")
    ax3.set_xlabel("Time [s]")
    ax3.set_ylabel("y [px] (smaller = higher)")
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    save_plot(fig3, plots_dir / "wrist_heights_px.png")

    fig4, ax4 = plt.subplots(figsize=(10, 4))
    ax4.plot(x, metrics_df["torso_tilt_deg"], color="tab:brown")
    ax4.set_title("Torso Tilt")
    ax4.set_xlabel("Time [s]")
    ax4.set_ylabel("Tilt from vertical [deg]")
    ax4.grid(True, alpha=0.3)
    save_plot(fig4, plots_dir / "torso_tilt_deg.png")

    fig5, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

    axes[0].plot(x, metrics_df["shoulder_height_diff_px"], color="tab:blue")
    axes[0].set_ylabel("Shoulder diff [px]")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(x, metrics_df["left_elbow_angle_deg"], label="Left", color="tab:green")
    axes[1].plot(x, metrics_df["right_elbow_angle_deg"], label="Right", color="tab:orange")
    axes[1].set_ylabel("Elbow angle [deg]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(x, metrics_df["left_wrist_y_px"], label="Left", color="tab:red")
    axes[2].plot(x, metrics_df["right_wrist_y_px"], label="Right", color="tab:purple")
    axes[2].set_ylabel("Wrist y [px]")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    axes[3].plot(x, metrics_df["torso_tilt_deg"], color="tab:brown")
    axes[3].set_ylabel("Torso tilt [deg]")
    axes[3].set_xlabel("Time [s]")
    axes[3].grid(True, alpha=0.3)

    save_plot(fig5, plots_dir / "combined_metrics.png")


def score_from_abs_mean(value, thresholds, scores):
    if pd.isna(value):
        return np.nan
    abs_value = abs(float(value))
    if abs_value <= thresholds[0]:
        return scores[0]
    if abs_value <= thresholds[1]:
        return scores[1]
    if abs_value <= thresholds[2]:
        return scores[2]
    return scores[3]


def score_from_std(value, thresholds, scores):
    if pd.isna(value):
        return np.nan
    std_value = float(value)
    if std_value <= thresholds[0]:
        return scores[0]
    if std_value <= thresholds[1]:
        return scores[1]
    if std_value <= thresholds[2]:
        return scores[2]
    return scores[3]


def grade_from_score(score):
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "E"


def build_auto_comment(primary_issue, secondary_issue, component_scores):
    messages = {
        "shoulder_unlevel": "左右の肩の高さ差が大きく、胴造りの安定に課題があります。",
        "torso_lean": "胴体の傾きが大きく、縦線の安定性に課題があります。",
        "elbow_line_bad": "左右の肘の収まりに差があり、引分けの均衡に課題があります。",
        "wrist_height_unstable": "左右の手首高さの差が大きく、上肢の収まりに課題があります。",
        "kai_unstable": "会の局面で揺れが大きく、静止性が十分ではありません。",
    }

    parts = []
    if primary_issue in messages:
        parts.append(messages[primary_issue])
    if secondary_issue in messages and secondary_issue != primary_issue:
        parts.append(messages[secondary_issue])

    best_name = max(component_scores, key=component_scores.get)
    strengths = {
        "shoulder_balance_score": "肩線の水平は比較的保たれています。",
        "torso_posture_score": "胴体の縦線は比較的安定しています。",
        "elbow_balance_score": "左右の肘角度は比較的揃っています。",
        "wrist_balance_score": "左右の手首高さは比較的揃っています。",
        "stillness_score": "全体の静止性は比較的良好です。",
    }
    if best_name in strengths and component_scores[best_name] >= 75:
        parts.append(strengths[best_name])

    if not parts:
        parts.append("大きな崩れは少なく、全体として安定した射型です。")

    return " ".join(parts)


def make_issue_message(issue_name):
    messages = {
        "shoulder_unlevel": "左右の肩の高さ差が大きい",
        "torso_lean": "胴体の傾きが大きい",
        "elbow_line_bad": "左右の肘の収まりに差がある",
        "wrist_height_unstable": "左右の手首高さの差が大きい",
        "kai_unstable": "静止性が不足している",
    }
    return messages.get(issue_name, issue_name)


def evaluate_rule_based(metrics_df):
    summary = {
        "mean_abs_shoulder_height_diff_px": float(
            metrics_df["shoulder_height_diff_px"].abs().mean(skipna=True)
        ),
        "mean_abs_torso_tilt_deg": float(
            metrics_df["torso_tilt_deg"].abs().mean(skipna=True)
        ),
        "mean_abs_elbow_angle_diff_deg": float(
            metrics_df["elbow_angle_diff_deg"].abs().mean(skipna=True)
        ),
        "mean_abs_wrist_height_diff_px": float(
            metrics_df["wrist_height_diff_px"].abs().mean(skipna=True)
        ),
        "shoulder_height_std_px": float(
            metrics_df["shoulder_height_diff_px"].std(skipna=True)
        ),
        "torso_tilt_std_deg": float(metrics_df["torso_tilt_deg"].std(skipna=True)),
        "wrist_height_std_px": float(
            metrics_df["wrist_height_diff_px"].std(skipna=True)
        ),
    }

    component_scores = {
        "shoulder_balance_score": score_from_abs_mean(
            summary["mean_abs_shoulder_height_diff_px"],
            thresholds=(10.0, 20.0, 35.0),
            scores=(95, 80, 60, 35),
        ),
        "torso_posture_score": score_from_abs_mean(
            summary["mean_abs_torso_tilt_deg"],
            thresholds=(3.0, 6.0, 10.0),
            scores=(95, 80, 60, 35),
        ),
        "elbow_balance_score": score_from_abs_mean(
            summary["mean_abs_elbow_angle_diff_deg"],
            thresholds=(8.0, 15.0, 25.0),
            scores=(95, 80, 60, 35),
        ),
        "wrist_balance_score": score_from_abs_mean(
            summary["mean_abs_wrist_height_diff_px"],
            thresholds=(12.0, 25.0, 45.0),
            scores=(95, 80, 60, 35),
        ),
        "stillness_score": np.nanmean(
            [
                score_from_std(
                    summary["shoulder_height_std_px"],
                    thresholds=(6.0, 12.0, 20.0),
                    scores=(95, 80, 60, 35),
                ),
                score_from_std(
                    summary["torso_tilt_std_deg"],
                    thresholds=(1.5, 3.0, 5.0),
                    scores=(95, 80, 60, 35),
                ),
                score_from_std(
                    summary["wrist_height_std_px"],
                    thresholds=(10.0, 20.0, 35.0),
                    scores=(95, 80, 60, 35),
                ),
            ]
        ),
    }

    weighted_scores = {
        "shoulder_balance_score": 0.20,
        "torso_posture_score": 0.25,
        "elbow_balance_score": 0.20,
        "wrist_balance_score": 0.15,
        "stillness_score": 0.20,
    }

    overall_score = 0.0
    total_weight = 0.0
    for name, weight in weighted_scores.items():
        value = component_scores[name]
        if not pd.isna(value):
            overall_score += float(value) * weight
            total_weight += weight

    overall_score = round(overall_score / total_weight, 1) if total_weight > 0 else np.nan
    overall_grade = grade_from_score(overall_score) if not pd.isna(overall_score) else "N/A"

    issue_candidates = [
        ("shoulder_unlevel", component_scores["shoulder_balance_score"]),
        ("torso_lean", component_scores["torso_posture_score"]),
        ("elbow_line_bad", component_scores["elbow_balance_score"]),
        ("wrist_height_unstable", component_scores["wrist_balance_score"]),
        ("kai_unstable", component_scores["stillness_score"]),
    ]
    issue_candidates.sort(key=lambda item: item[1])

    primary_issue = issue_candidates[0][0]
    secondary_issue = issue_candidates[1][0]

    issue_tags = [
        name for name, score in issue_candidates if not pd.isna(score) and score < 75
    ]

    auto_comment = build_auto_comment(primary_issue, secondary_issue, component_scores)

    return {
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "primary_issue": primary_issue,
        "secondary_issue": secondary_issue,
        "issue_tags": issue_tags,
        "auto_comment": auto_comment,
        "component_scores": {
            key: round(float(value), 1) for key, value in component_scores.items()
        },
        "summary_metrics": {key: round(float(value), 2) for key, value in summary.items()},
    }


def evaluate_window(window_df):
    summary = {
        "mean_abs_shoulder_height_diff_px": float(
            window_df["shoulder_height_diff_px"].abs().mean(skipna=True)
        ),
        "mean_abs_torso_tilt_deg": float(
            window_df["torso_tilt_deg"].abs().mean(skipna=True)
        ),
        "mean_abs_elbow_angle_diff_deg": float(
            window_df["elbow_angle_diff_deg"].abs().mean(skipna=True)
        ),
        "mean_abs_wrist_height_diff_px": float(
            window_df["wrist_height_diff_px"].abs().mean(skipna=True)
        ),
        "shoulder_height_std_px": float(
            window_df["shoulder_height_diff_px"].std(skipna=True)
        ),
        "torso_tilt_std_deg": float(window_df["torso_tilt_deg"].std(skipna=True)),
        "wrist_height_std_px": float(window_df["wrist_height_diff_px"].std(skipna=True)),
    }

    component_scores = {
        "shoulder_balance_score": score_from_abs_mean(
            summary["mean_abs_shoulder_height_diff_px"], (10.0, 20.0, 35.0), (95, 80, 60, 35)
        ),
        "torso_posture_score": score_from_abs_mean(
            summary["mean_abs_torso_tilt_deg"], (3.0, 6.0, 10.0), (95, 80, 60, 35)
        ),
        "elbow_balance_score": score_from_abs_mean(
            summary["mean_abs_elbow_angle_diff_deg"], (8.0, 15.0, 25.0), (95, 80, 60, 35)
        ),
        "wrist_balance_score": score_from_abs_mean(
            summary["mean_abs_wrist_height_diff_px"], (12.0, 25.0, 45.0), (95, 80, 60, 35)
        ),
        "stillness_score": np.nanmean(
            [
                score_from_std(summary["shoulder_height_std_px"], (6.0, 12.0, 20.0), (95, 80, 60, 35)),
                score_from_std(summary["torso_tilt_std_deg"], (1.5, 3.0, 5.0), (95, 80, 60, 35)),
                score_from_std(summary["wrist_height_std_px"], (10.0, 20.0, 35.0), (95, 80, 60, 35)),
            ]
        ),
    }

    issue_candidates = [
        ("shoulder_unlevel", component_scores["shoulder_balance_score"]),
        ("torso_lean", component_scores["torso_posture_score"]),
        ("elbow_line_bad", component_scores["elbow_balance_score"]),
        ("wrist_height_unstable", component_scores["wrist_balance_score"]),
        ("kai_unstable", component_scores["stillness_score"]),
    ]
    issue_candidates.sort(key=lambda item: item[1])
    return component_scores, issue_candidates


def build_timeline_annotations(metrics_df, window_sec=0.75, step_sec=0.25, score_threshold=70):
    valid_ts = metrics_df["timestamp_sec"].dropna()
    if valid_ts.empty:
        return {"timeline_windows": [], "issue_segments": []}

    start_ts = float(valid_ts.min())
    end_ts = float(valid_ts.max())
    window_rows = []

    current = start_ts
    while current <= end_ts:
        window_end = current + window_sec
        window_df = metrics_df[
            (metrics_df["timestamp_sec"] >= current) & (metrics_df["timestamp_sec"] < window_end)
        ]
        if not window_df.empty:
            component_scores, issue_candidates = evaluate_window(window_df)
            primary_issue, primary_score = issue_candidates[0]
            row = {
                "start_sec": round(current, 2),
                "end_sec": round(window_end, 2),
                "primary_issue": primary_issue,
                "primary_score": round(float(primary_score), 1),
            }
            for key, value in component_scores.items():
                row[key] = round(float(value), 1)
            window_rows.append(row)
        current += step_sec

    segments = []
    issue_order = [
        "shoulder_unlevel",
        "torso_lean",
        "elbow_line_bad",
        "wrist_height_unstable",
        "kai_unstable",
    ]
    for issue_name in issue_order:
        active_segment = None
        for row in window_rows:
            score_key = {
                "shoulder_unlevel": "shoulder_balance_score",
                "torso_lean": "torso_posture_score",
                "elbow_line_bad": "elbow_balance_score",
                "wrist_height_unstable": "wrist_balance_score",
                "kai_unstable": "stillness_score",
            }[issue_name]
            if row[score_key] < score_threshold:
                if active_segment is None:
                    active_segment = {
                        "issue": issue_name,
                        "label": make_issue_message(issue_name),
                        "start_sec": row["start_sec"],
                        "end_sec": row["end_sec"],
                        "worst_score": row[score_key],
                    }
                else:
                    gap = row["start_sec"] - active_segment["end_sec"]
                    if gap <= step_sec + 1e-6:
                        active_segment["end_sec"] = row["end_sec"]
                        active_segment["worst_score"] = min(active_segment["worst_score"], row[score_key])
                    else:
                        segments.append(active_segment)
                        active_segment = {
                            "issue": issue_name,
                            "label": make_issue_message(issue_name),
                            "start_sec": row["start_sec"],
                            "end_sec": row["end_sec"],
                            "worst_score": row[score_key],
                        }
            elif active_segment is not None:
                segments.append(active_segment)
                active_segment = None
        if active_segment is not None:
            segments.append(active_segment)

    segments.sort(key=lambda x: (x["start_sec"], x["worst_score"]))
    for segment in segments:
        segment["start_sec"] = round(float(segment["start_sec"]), 2)
        segment["end_sec"] = round(float(segment["end_sec"]), 2)
        segment["worst_score"] = round(float(segment["worst_score"]), 1)
        segment["comment"] = f"{segment['start_sec']:.2f}s-{segment['end_sec']:.2f}s: {segment['label']}"

    return {"timeline_windows": window_rows, "issue_segments": segments}


def find_longest_true_segment(mask, timestamps):
    best = None
    start_idx = None
    for idx, active in enumerate(mask):
        if active and start_idx is None:
            start_idx = idx
        elif not active and start_idx is not None:
            segment = (start_idx, idx - 1)
            if best is None or (segment[1] - segment[0]) > (best[1] - best[0]):
                best = segment
            start_idx = None
    if start_idx is not None:
        segment = (start_idx, len(mask) - 1)
        if best is None or (segment[1] - segment[0]) > (best[1] - best[0]):
            best = segment
    return best


def infer_phase_segments(metrics_df):
    if metrics_df.empty or metrics_df["timestamp_sec"].dropna().empty:
        return []

    df = metrics_df.copy().reset_index(drop=True)
    if len(df) < 2:
        return []

    ts = df["timestamp_sec"].astype(float)
    total_start = float(ts.iloc[0])
    total_end = float(ts.iloc[-1])
    total_duration = max(total_end - total_start, 1e-6)

    wrist_mean_y = df[["left_wrist_y_px", "right_wrist_y_px"]].mean(axis=1, skipna=True)
    wrist_mean_y = wrist_mean_y.interpolate(limit_direction="both")
    torso_tilt = df["torso_tilt_deg"].interpolate(limit_direction="both").fillna(0.0)
    wrist_diff = df["wrist_height_diff_px"].interpolate(limit_direction="both").fillna(0.0)

    dt = ts.diff().replace(0, np.nan).fillna(method="bfill").fillna(method="ffill").fillna(1 / 30)
    motion = (
        wrist_mean_y.diff().abs().fillna(0.0)
        + 0.5 * wrist_diff.diff().abs().fillna(0.0)
        + 3.0 * torso_tilt.diff().abs().fillna(0.0)
    )
    motion_smooth = motion.rolling(window=7, min_periods=1, center=True).mean()

    upward_velocity = (-wrist_mean_y.diff() / dt).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    significant_up = upward_velocity > max(upward_velocity.quantile(0.8), 2.0)
    uchiokoshi_start_idx = int(significant_up.idxmax()) if significant_up.any() else max(1, int(len(df) * 0.15))

    valid_before_end = ts <= (total_start + total_duration * 0.75)
    if valid_before_end.any():
        candidate_series = wrist_mean_y.where(valid_before_end, np.nan)
        uchiokoshi_end_idx = int(candidate_series.idxmin())
    else:
        uchiokoshi_end_idx = max(uchiokoshi_start_idx + 1, int(len(df) * 0.35))

    kai_zone_mask = (ts >= (total_start + total_duration * 0.35)) & (
        ts <= (total_start + total_duration * 0.9)
    )
    still_mask = (motion_smooth <= motion_smooth.quantile(0.35)) & kai_zone_mask
    longest_still = find_longest_true_segment(still_mask.tolist(), ts.tolist())

    if longest_still is None:
        kai_start_idx = max(uchiokoshi_end_idx + 1, int(len(df) * 0.55))
        kai_end_idx = max(kai_start_idx + 1, int(len(df) * 0.7))
    else:
        kai_start_idx, kai_end_idx = longest_still

    if kai_start_idx <= uchiokoshi_end_idx:
        kai_start_idx = min(len(df) - 2, uchiokoshi_end_idx + 1)
    if kai_end_idx <= kai_start_idx:
        kai_end_idx = min(len(df) - 1, kai_start_idx + 1)

    hanare_start_idx = kai_end_idx
    hanare_end_idx = min(len(df) - 1, hanare_start_idx + max(1, int(len(df) * 0.05)))
    zanshin_start_idx = min(len(df) - 1, hanare_end_idx)

    pre_uchi_duration = max(ts.iloc[uchiokoshi_start_idx] - total_start, total_duration * 0.12)
    ashibumi_end = total_start + pre_uchi_duration / 3.0
    dozukuri_end = total_start + 2.0 * pre_uchi_duration / 3.0
    yugamae_end = total_start + pre_uchi_duration

    def clip_time(value):
        return round(float(min(max(value, total_start), total_end)), 2)

    segments = [
        {"phase_name": "ashibumi", "start_sec": clip_time(total_start), "end_sec": clip_time(ashibumi_end), "confidence": "low"},
        {"phase_name": "dozukuri", "start_sec": clip_time(ashibumi_end), "end_sec": clip_time(dozukuri_end), "confidence": "low"},
        {"phase_name": "yugamae", "start_sec": clip_time(dozukuri_end), "end_sec": clip_time(yugamae_end), "confidence": "low"},
        {"phase_name": "uchiokoshi", "start_sec": clip_time(ts.iloc[uchiokoshi_start_idx]), "end_sec": clip_time(ts.iloc[uchiokoshi_end_idx]), "confidence": "medium"},
        {"phase_name": "hikiwake", "start_sec": clip_time(ts.iloc[uchiokoshi_end_idx]), "end_sec": clip_time(ts.iloc[kai_start_idx]), "confidence": "medium"},
        {"phase_name": "kai", "start_sec": clip_time(ts.iloc[kai_start_idx]), "end_sec": clip_time(ts.iloc[kai_end_idx]), "confidence": "medium"},
        {"phase_name": "hanare", "start_sec": clip_time(ts.iloc[hanare_start_idx]), "end_sec": clip_time(ts.iloc[hanare_end_idx]), "confidence": "low"},
        {"phase_name": "zanshin", "start_sec": clip_time(ts.iloc[zanshin_start_idx]), "end_sec": clip_time(total_end), "confidence": "medium"},
    ]

    cleaned_segments = []
    previous_end = total_start
    for segment in segments:
        start_sec = max(segment["start_sec"], round(previous_end, 2))
        end_sec = max(start_sec, segment["end_sec"])
        cleaned_segments.append(
            {
                "phase_name": segment["phase_name"],
                "start_sec": round(start_sec, 2),
                "end_sec": round(end_sec, 2),
                "duration_sec": round(max(end_sec - start_sec, 0.0), 2),
                "confidence": segment["confidence"],
            }
        )
        previous_end = end_sec

    return cleaned_segments


def compute_phase_score(segment_df, phase_name):
    base_eval = evaluate_rule_based(segment_df)
    component_scores = base_eval["component_scores"]

    phase_weights = {
        "ashibumi": {"torso_posture_score": 0.45, "shoulder_balance_score": 0.35, "stillness_score": 0.20},
        "dozukuri": {"torso_posture_score": 0.50, "shoulder_balance_score": 0.30, "stillness_score": 0.20},
        "yugamae": {"shoulder_balance_score": 0.30, "wrist_balance_score": 0.35, "stillness_score": 0.35},
        "uchiokoshi": {"shoulder_balance_score": 0.30, "wrist_balance_score": 0.35, "torso_posture_score": 0.35},
        "hikiwake": {"elbow_balance_score": 0.40, "torso_posture_score": 0.35, "wrist_balance_score": 0.25},
        "kai": {"stillness_score": 0.45, "shoulder_balance_score": 0.20, "torso_posture_score": 0.20, "wrist_balance_score": 0.15},
        "hanare": {"stillness_score": 0.30, "torso_posture_score": 0.40, "elbow_balance_score": 0.30},
        "zanshin": {"stillness_score": 0.40, "torso_posture_score": 0.35, "shoulder_balance_score": 0.25},
    }
    weights = phase_weights[phase_name]

    weighted_sum = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        value = component_scores.get(key, np.nan)
        if not pd.isna(value):
            weighted_sum += float(value) * weight
            total_weight += weight
    phase_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else np.nan

    issue_candidates = [
        ("shoulder_unlevel", component_scores["shoulder_balance_score"]),
        ("torso_lean", component_scores["torso_posture_score"]),
        ("elbow_line_bad", component_scores["elbow_balance_score"]),
        ("wrist_height_unstable", component_scores["wrist_balance_score"]),
        ("kai_unstable", component_scores["stillness_score"]),
    ]
    issue_candidates.sort(key=lambda item: item[1])
    phase_issue = issue_candidates[0][0]

    return phase_score, grade_from_score(phase_score), phase_issue


def build_phase_evaluation(metrics_df):
    phase_segments = infer_phase_segments(metrics_df)
    phase_evaluations = []
    for segment in phase_segments:
        segment_df = metrics_df[
            (metrics_df["timestamp_sec"] >= segment["start_sec"])
            & (metrics_df["timestamp_sec"] <= segment["end_sec"])
        ]
        if segment_df.empty:
            continue
        phase_score, phase_grade, phase_issue = compute_phase_score(
            segment_df, segment["phase_name"]
        )
        phase_evaluations.append(
            {
                "phase_name": segment["phase_name"],
                "start_sec": segment["start_sec"],
                "end_sec": segment["end_sec"],
                "duration_sec": segment["duration_sec"],
                "confidence": segment["confidence"],
                "phase_score": phase_score,
                "phase_grade": phase_grade,
                "primary_issue": phase_issue,
            }
        )
    return phase_evaluations


def analyze_pose_csv(csv_path, output_dir, score_thr=0.3):
    csv_path = Path(csv_path)
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    metrics_df = analyze_keypoints_df(df, score_thr=score_thr)
    evaluation_summary = evaluate_rule_based(metrics_df)
    evaluation_timeline = build_timeline_annotations(metrics_df)
    phase_evaluations = build_phase_evaluation(metrics_df)

    metrics_path = output_dir / "metrics.csv"
    evaluation_path = output_dir / "evaluation_summary.json"
    timeline_path = output_dir / "evaluation_timeline.json"
    phase_path = output_dir / "phase_evaluation.json"
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8")
    plot_metrics(metrics_df, plots_dir)
    with evaluation_path.open("w", encoding="utf-8") as f:
        json.dump(evaluation_summary, f, ensure_ascii=False, indent=2)
    with timeline_path.open("w", encoding="utf-8") as f:
        json.dump(evaluation_timeline, f, ensure_ascii=False, indent=2)
    with phase_path.open("w", encoding="utf-8") as f:
        json.dump(phase_evaluations, f, ensure_ascii=False, indent=2)

    return {
        "metrics_path": metrics_path,
        "evaluation_path": evaluation_path,
        "timeline_path": timeline_path,
        "phase_path": phase_path,
        "plots_dir": plots_dir,
        "metrics_df": metrics_df,
        "evaluation_summary": evaluation_summary,
        "evaluation_timeline": evaluation_timeline,
        "phase_evaluations": phase_evaluations,
    }


def main():
    args = parse_args()
    result = analyze_pose_csv(
        csv_path=args.csv,
        output_dir=args.output_dir,
        score_thr=args.score_thr,
    )
    print(f"Saved metrics CSV: {result['metrics_path']}")
    print(f"Saved evaluation summary: {result['evaluation_path']}")
    print(f"Saved evaluation timeline: {result['timeline_path']}")
    print(f"Saved phase evaluation: {result['phase_path']}")
    print(f"Saved plots directory: {result['plots_dir']}")


if __name__ == "__main__":
    main()
