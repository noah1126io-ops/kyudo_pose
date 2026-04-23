from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analyze_pose_csv import analyze_pose_csv
from run_pose_video import run_pose_video


APP_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = APP_ROOT / "data" / "uploads"
OUTPUT_ROOT = APP_ROOT / "outputs"


def make_run_dir(stem):
    safe_stem = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_ROOT / f"{timestamp}_{safe_stem}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_uploaded_video(uploaded_file, run_dir):
    upload_dir = run_dir / "input"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix or ".mp4"
    input_path = upload_dir / f"uploaded_video{suffix}"
    with input_path.open("wb") as f:
        f.write(uploaded_file.getbuffer())
    return input_path


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def render_summary(metrics_df):
    st.subheader("Summary")
    summary = {
        "Frames": int(metrics_df["frame_index"].count()),
        "Shoulder diff mean [px]": float(metrics_df["shoulder_height_diff_px"].mean(skipna=True)),
        "Left elbow angle mean [deg]": float(metrics_df["left_elbow_angle_deg"].mean(skipna=True)),
        "Right elbow angle mean [deg]": float(metrics_df["right_elbow_angle_deg"].mean(skipna=True)),
        "Torso tilt mean [deg]": float(metrics_df["torso_tilt_deg"].mean(skipna=True)),
    }
    st.dataframe(pd.DataFrame([summary]), use_container_width=True)


def render_rule_based_evaluation(evaluation_summary):
    st.subheader("ルールベース評価")

    overview = pd.DataFrame(
        [
            {
                "総合点": evaluation_summary["overall_score"],
                "評価": evaluation_summary["overall_grade"],
                "主問題": evaluation_summary["primary_issue"],
                "副問題": evaluation_summary["secondary_issue"],
            }
        ]
    )
    st.dataframe(overview, use_container_width=True)

    st.write(evaluation_summary["auto_comment"])

    component_scores = pd.DataFrame(
        [
            {
                "肩線バランス": evaluation_summary["component_scores"]["shoulder_balance_score"],
                "胴造り": evaluation_summary["component_scores"]["torso_posture_score"],
                "肘の均衡": evaluation_summary["component_scores"]["elbow_balance_score"],
                "手首高さ": evaluation_summary["component_scores"]["wrist_balance_score"],
                "静止性": evaluation_summary["component_scores"]["stillness_score"],
            }
        ]
    )
    st.dataframe(component_scores, use_container_width=True)

    if evaluation_summary["issue_tags"]:
        st.caption("問題タグ: " + ", ".join(evaluation_summary["issue_tags"]))


def main():
    st.set_page_config(page_title="Kyudo Pose Analyzer", layout="wide")

    st.title("Kyudo Pose Analyzer")
    st.write("RTMPose / MMPose を使って、弓道動画をアップロードして姿勢推定と簡易分析を行います。")

    with st.sidebar:
        st.header("Settings")
        pose2d = st.selectbox("Pose model alias", ["human"], index=0)
        device = st.text_input("Device", value="cpu", help='例: cpu, cuda:0')
        score_thr = st.slider("Keypoint score threshold", 0.0, 1.0, 0.3, 0.05)
        kpt_thr = st.slider("Visualization threshold", 0.0, 1.0, 0.3, 0.05)
        radius = st.slider("Keypoint radius", 1, 10, 4)
        thickness = st.slider("Line thickness", 1, 6, 2)

    uploaded_file = st.file_uploader(
        "Upload a kyudo video",
        type=["mp4", "mov", "avi", "mkv"],
        accept_multiple_files=False,
    )

    if uploaded_file is None:
        st.info("動画を 1 本アップロードすると、可視化動画と分析結果を生成します。")
        return

    st.video(uploaded_file)

    if not st.button("Run analysis", type="primary"):
        return

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    run_dir = make_run_dir(Path(uploaded_file.name).stem)
    input_path = save_uploaded_video(uploaded_file, run_dir)

    progress_bar = st.progress(0.0, text="Preparing inference...")
    status_box = st.empty()

    def update_progress(done_frames, total_frames):
        if total_frames and total_frames > 0:
            ratio = min(done_frames / total_frames, 1.0)
            progress_bar.progress(ratio, text=f"Pose inference: {done_frames}/{total_frames} frames")
        else:
            progress_bar.progress(0.0, text=f"Pose inference: {done_frames} frames")

    try:
        status_box.write("Running pose estimation...")
        pose_result = run_pose_video(
            input_path=input_path,
            output_dir=run_dir,
            pose2d=pose2d,
            device=device.strip() or None,
            kpt_thr=kpt_thr,
            radius=radius,
            thickness=thickness,
            progress_callback=update_progress,
        )

        status_box.write("Analyzing keypoints...")
        analysis_result = analyze_pose_csv(
            csv_path=pose_result["csv_path"],
            output_dir=run_dir,
            score_thr=score_thr,
        )
        progress_bar.progress(1.0, text="Completed")
    except Exception as exc:
        progress_bar.empty()
        status_box.error(f"Analysis failed: {exc}")
        return

    metrics_df = analysis_result["metrics_df"]
    evaluation_summary = analysis_result["evaluation_summary"]

    st.success("分析が完了しました。")
    st.subheader("出力動画")
    st.video(read_bytes(pose_result["overlay_video"]), format="video/mp4")
    if pose_result.get("video_codec") == "mp4v":
        st.warning(
            "出力動画は mp4v で保存されました。ブラウザによっては埋め込み再生できないため、ダウンロードして再生してください。"
        )

    render_summary(metrics_df)
    render_rule_based_evaluation(evaluation_summary)

    st.subheader("時系列指標テーブル")
    st.dataframe(metrics_df, use_container_width=True)

    st.subheader("グラフ")
    plot_files = [
        "combined_metrics.png",
        "shoulder_height_diff_px.png",
        "elbow_angles_deg.png",
        "wrist_heights_px.png",
        "torso_tilt_deg.png",
    ]
    for plot_name in plot_files:
        plot_path = analysis_result["plots_dir"] / plot_name
        if plot_path.exists():
            st.image(str(plot_path), caption=plot_name, use_container_width=True)

    st.subheader("ダウンロード")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.download_button(
            "Download pose_overlay.mp4",
            data=read_bytes(pose_result["overlay_video"]),
            file_name="pose_overlay.mp4",
            mime="video/mp4",
        )
    with col2:
        st.download_button(
            "Download keypoints.csv",
            data=read_bytes(pose_result["csv_path"]),
            file_name="keypoints.csv",
            mime="text/csv",
        )
    with col3:
        st.download_button(
            "Download keypoints.json",
            data=read_bytes(pose_result["json_path"]),
            file_name="keypoints.json",
            mime="application/json",
        )
    with col4:
        st.download_button(
            "Download metrics.csv",
            data=read_bytes(analysis_result["metrics_path"]),
            file_name="metrics.csv",
            mime="text/csv",
        )
    with col5:
        st.download_button(
            "Download evaluation_summary.json",
            data=read_bytes(analysis_result["evaluation_path"]),
            file_name="evaluation_summary.json",
            mime="application/json",
        )

    st.caption(f"Saved run directory: {run_dir}")


if __name__ == "__main__":
    main()
