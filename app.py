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
    st.subheader("基本サマリー")
    summary = {
        "解析フレーム数": int(metrics_df["frame_index"].count()),
        "肩高さ差 平均[px]": float(metrics_df["shoulder_height_diff_px"].mean(skipna=True)),
        "左肘角度 平均[deg]": float(metrics_df["left_elbow_angle_deg"].mean(skipna=True)),
        "右肘角度 平均[deg]": float(metrics_df["right_elbow_angle_deg"].mean(skipna=True)),
        "胴体傾き 平均[deg]": float(metrics_df["torso_tilt_deg"].mean(skipna=True)),
    }
    st.dataframe(pd.DataFrame([summary]), use_container_width=True)


ISSUE_LABELS = {
    "shoulder_unlevel": "肩線の左右差",
    "torso_lean": "胴体の傾き",
    "elbow_line_bad": "左右の肘の収まり",
    "wrist_height_unstable": "左右の手首高さ",
    "kai_unstable": "静止性",
}


COMPONENT_LABELS = {
    "shoulder_balance_score": "肩線バランス",
    "torso_posture_score": "胴体の安定",
    "elbow_balance_score": "肘の均衡",
    "wrist_balance_score": "手首高さの均衡",
    "stillness_score": "静止性",
}


PHASE_LABELS = {
    "ashibumi": "足踏み",
    "dozukuri": "胴造り",
    "yugamae": "弓構え",
    "uchiokoshi": "打起し",
    "hikiwake": "引分け",
    "kai": "会",
    "hanare": "離れ",
    "zanshin": "残心",
}


def score_to_status(score):
    if score >= 90:
        return "非常に良い"
    if score >= 75:
        return "良い"
    if score >= 60:
        return "要観察"
    return "要修正"


def build_user_guidance(evaluation_summary):
    primary_issue = evaluation_summary["primary_issue"]
    secondary_issue = evaluation_summary["secondary_issue"]
    guidance_map = {
        "shoulder_unlevel": "肩の高さが左右で揃うかを優先して確認してください。特に胴造りから会にかけて肩が上下しないかを見るのが有効です。",
        "torso_lean": "胴体の縦線が保てているかを確認してください。引分けから残心まで上体が左右へ流れないかを重点的に見るとよいです。",
        "elbow_line_bad": "左右の肘の収まりに差があります。引分けから会にかけて、肘の高さや開き方が揃っているかを見直してください。",
        "wrist_height_unstable": "左右の手首高さに差が出ています。会の場面で手先の高さが安定しているかを確認してください。",
        "kai_unstable": "会の静止性が不足しています。会で止まり切れているか、離れ直前に余計な揺れがないかを確認してください。",
    }
    suggestions = []
    for issue in [primary_issue, secondary_issue]:
        if issue in guidance_map and guidance_map[issue] not in suggestions:
            suggestions.append(guidance_map[issue])
    return suggestions


def render_rule_based_evaluation(evaluation_summary):
    st.subheader("ユーザー向け要約")

    overview = pd.DataFrame(
        [
            {
                "総合点": evaluation_summary["overall_score"],
                "評価": evaluation_summary["overall_grade"],
                "主問題": ISSUE_LABELS.get(
                    evaluation_summary["primary_issue"], evaluation_summary["primary_issue"]
                ),
                "副問題": ISSUE_LABELS.get(
                    evaluation_summary["secondary_issue"], evaluation_summary["secondary_issue"]
                ),
            }
        ]
    )
    st.dataframe(overview, use_container_width=True)

    st.write(evaluation_summary["auto_comment"])
    guidance = build_user_guidance(evaluation_summary)
    if guidance:
        st.subheader("ユーザー向け修正ポイント")
        for text in guidance:
            st.write(f"- {text}")

    st.subheader("ユーザー向け詳細")
    component_scores = pd.DataFrame(
        [
            {
                "肩線バランス": f"{evaluation_summary['component_scores']['shoulder_balance_score']} ({score_to_status(evaluation_summary['component_scores']['shoulder_balance_score'])})",
                "胴体の安定": f"{evaluation_summary['component_scores']['torso_posture_score']} ({score_to_status(evaluation_summary['component_scores']['torso_posture_score'])})",
                "肘の均衡": f"{evaluation_summary['component_scores']['elbow_balance_score']} ({score_to_status(evaluation_summary['component_scores']['elbow_balance_score'])})",
                "手首高さの均衡": f"{evaluation_summary['component_scores']['wrist_balance_score']} ({score_to_status(evaluation_summary['component_scores']['wrist_balance_score'])})",
                "静止性": f"{evaluation_summary['component_scores']['stillness_score']} ({score_to_status(evaluation_summary['component_scores']['stillness_score'])})",
            }
        ]
    )
    st.dataframe(component_scores, use_container_width=True)

    if evaluation_summary["issue_tags"]:
        labels = [ISSUE_LABELS.get(tag, tag) for tag in evaluation_summary["issue_tags"]]
        st.caption("問題タグ: " + ", ".join(labels))


def render_timeline_annotations(evaluation_timeline):
    st.subheader("問題が出た時間帯")
    issue_segments = evaluation_timeline.get("issue_segments", [])
    if not issue_segments:
        st.write("明確な問題区間はまだ抽出されていません。")
        return

    segment_rows = []
    for segment in issue_segments:
        segment_rows.append(
            {
                "開始[s]": segment["start_sec"],
                "終了[s]": segment["end_sec"],
                "問題": ISSUE_LABELS.get(segment["issue"], segment["issue"]),
                "説明": segment["label"],
                "最悪スコア": segment["worst_score"],
            }
        )

    st.dataframe(pd.DataFrame(segment_rows), use_container_width=True)
    st.caption("時間帯コメント: " + " / ".join(segment["comment"] for segment in issue_segments[:5]))


def render_phase_evaluation(phase_evaluations):
    st.subheader("射法八節ごとの評価")
    if not phase_evaluations:
        st.write("八節評価はまだ算出されていません。")
        return
    st.caption("注: 八節の区間と長さは現時点では動画特徴量からの推定です。")

    rows = []
    kai_duration = None
    for phase in phase_evaluations:
        rows.append(
            {
                "八節": PHASE_LABELS.get(phase["phase_name"], phase["phase_name"]),
                "評価点": phase["phase_score"],
                "評価": phase["phase_grade"],
                "開始[s]": phase["start_sec"],
                "終了[s]": phase["end_sec"],
                "長さ[s]": phase["duration_sec"],
                "主問題": ISSUE_LABELS.get(phase["primary_issue"], phase["primary_issue"]),
                "推定信頼度": phase["confidence"],
            }
        )
        if phase["phase_name"] == "kai":
            kai_duration = phase["duration_sec"]

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    if kai_duration is not None:
        st.caption(f"会の長さ（推定）: {kai_duration:.2f} 秒")


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
    evaluation_timeline = analysis_result["evaluation_timeline"]
    phase_evaluations = analysis_result["phase_evaluations"]

    st.success("分析が完了しました。")
    st.subheader("出力動画")
    st.video(read_bytes(pose_result["overlay_video"]), format="video/mp4")
    if pose_result.get("video_codec") == "mp4v":
        st.warning(
            "出力動画は mp4v で保存されました。ブラウザによっては埋め込み再生できないため、ダウンロードして再生してください。"
        )

    render_summary(metrics_df)
    render_rule_based_evaluation(evaluation_summary)
    render_timeline_annotations(evaluation_timeline)
    render_phase_evaluation(phase_evaluations)

    with st.expander("詳細を見る"):
        st.subheader("時系列指標テーブル")
        st.dataframe(metrics_df, use_container_width=True)

        st.subheader("グラフ")
        plot_files = [
            "combined_metrics.png",
            "shoulder_height_diff_px.png",
            "elbow_angles_deg.png",
            "wrist_heights_px.png",
            "hand_tip_heights_px.png",
            "torso_tilt_deg.png",
        ]
        for plot_name in plot_files:
            plot_path = analysis_result["plots_dir"] / plot_name
            if plot_path.exists():
                st.image(str(plot_path), caption=plot_name, use_container_width=True)

        st.caption("手先点は現時点では手首そのものではなく、肘-手首ベクトルを前方へ延長した推定点です。")

    with st.expander("開発者向け情報"):
        st.subheader("ダウンロード")
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1:
            st.download_button(
                "動画",
                data=read_bytes(pose_result["overlay_video"]),
                file_name="pose_overlay.mp4",
                mime="video/mp4",
            )
        with col2:
            st.download_button(
                "keypoints.csv",
                data=read_bytes(pose_result["csv_path"]),
                file_name="keypoints.csv",
                mime="text/csv",
            )
        with col3:
            st.download_button(
                "keypoints.json",
                data=read_bytes(pose_result["json_path"]),
                file_name="keypoints.json",
                mime="application/json",
            )
        with col4:
            st.download_button(
                "metrics.csv",
                data=read_bytes(analysis_result["metrics_path"]),
                file_name="metrics.csv",
                mime="text/csv",
            )
        with col5:
            st.download_button(
                "evaluation_summary.json",
                data=read_bytes(analysis_result["evaluation_path"]),
                file_name="evaluation_summary.json",
                mime="application/json",
            )
        with col6:
            st.download_button(
                "evaluation_timeline.json",
                data=read_bytes(analysis_result["timeline_path"]),
                file_name="evaluation_timeline.json",
                mime="application/json",
            )
        with col7:
            st.download_button(
                "phase_evaluation.json",
                data=read_bytes(analysis_result["phase_path"]),
                file_name="phase_evaluation.json",
                mime="application/json",
            )

    st.caption(f"Saved run directory: {run_dir}")


if __name__ == "__main__":
    main()
