# kyudo_pose

Windows で RTMPose / MMPose を使い、弓道動画をアップロードして姿勢推定と簡易分析を行う最小アプリです。

このプロジェクトでできること:

- 単一人物の弓道動画を入力
- 各フレームで 2D キーポイント推定
- 可視化動画を書き出し
- キーポイントを CSV / JSON で保存
- 次の指標を計算してグラフ化
  - 左右肩の高さ差
  - 肩-肘-手首角度
  - 手首の高さ時系列
  - 推定した手先点の高さ時系列
  - 胴体の傾き
- Streamlit の画面から動画アップロードと分析実行

最小構成を優先し、MMPose の `MMPoseInferencer` を使用しています。

## ファイル構成

```text
kyudo_pose/
├─ README.md
├─ environment.yml
├─ app.py
├─ run_pose_video.py
├─ analyze_pose_csv.py
├─ data/
│  ├─ input/
│  └─ uploads/
└─ outputs/
   └─ 20260422_123456_sample/
      ├─ input/
      │  └─ uploaded_video.mp4
      ├─ pose_overlay.mp4
      ├─ keypoints.csv
      ├─ keypoints.json
      ├─ metrics.csv
      └─ plots/
         ├─ combined_metrics.png
         ├─ shoulder_height_diff_px.png
         ├─ elbow_angles_deg.png
         ├─ wrist_heights_px.png
         └─ torso_tilt_deg.png
```

## 1. Conda 環境作成

```bash
conda env create -f environment.yml
conda activate kyudo-pose
```

## 2. PyTorch のインストール

PyTorch は CUDA の有無でコマンドが変わるため、公式ページの案内に合わせて入れてください。

- PyTorch 公式:
  https://pytorch.org/get-started/locally/

例: CPU のみ

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

例: CUDA 12.1

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 3. MMPose / OpenMMLab 依存のインストール

MMPose 公式の推論ガイドとインストールガイド:

- Inference:
  https://mmpose.readthedocs.io/en/latest/user_guides/inference.html
- Installation:
  https://mmpose.readthedocs.io/en/dev-1.x/installation.html

この最小版は単一人物前提なので、`det_model='whole_image'` を使って人物検出モデル依存を減らしています。

```bash
pip install -U openmim
mim install mmengine
mim install "mmcv>=2.0.0"
pip install "mmpose>=1.3.0"
```

確認:

```bash
python -c "from mmpose.apis import MMPoseInferencer; print('MMPose OK')"
```

## 4. アプリの起動

```bash
streamlit run app.py
```

起動後、ブラウザでローカル URL が開きます。動画をアップロードして `Run analysis` を押すと、可視化動画と分析結果が生成されます。

## 5. Spyder から使う場合

Spyder でアプリを直接動かすより、まず以下のどちらかが扱いやすいです。

1. `app.py` を開いて `Run`
2. IPython Console から `streamlit run app.py` を実行

CLI スクリプトを Spyder から使うこともできます。

```python
runfile("run_pose_video.py", args="--input data/input/sample.mp4 --output-dir outputs/sample_run", wdir=r"C:\Users\YOUR_NAME\Desktop\kyudo_pose")
runfile("analyze_pose_csv.py", args="--csv outputs/sample_run/keypoints.csv --output-dir outputs/sample_run", wdir=r"C:\Users\YOUR_NAME\Desktop\kyudo_pose")
```

## 6. CLI で実行する場合

姿勢推定:

```bash
python run_pose_video.py --input data/input/sample.mp4 --output-dir outputs/sample_run
```

分析:

```bash
python analyze_pose_csv.py --csv outputs/sample_run/keypoints.csv --output-dir outputs/sample_run
```

GPU を使う例:

```bash
python run_pose_video.py --input data/input/sample.mp4 --output-dir outputs/sample_run --device cuda:0
```

## 出力

- `pose_overlay.mp4`
- `keypoints.csv`
- `keypoints.json`
- `metrics.csv`
- `plots/*.png`

## 実装方針

- 2D モデルの既定値は `human`
  - MMPose の公式 Inference ガイドで、`human` は RTMPose-m ベースの human alias として案内されています。
- 単一人物前提なので `det_model='whole_image'` を使用
  - フレーム全体を人物領域として扱います。
- キーポイント形式は COCO 17 点前提です。
- 手先点は現時点では COCO 17 点に含まれないため、肘-手首ベクトルを手先方向に延長した推定点として扱います。

## 指標の意味

- 左右肩の高さ差:
  `left_shoulder_y - right_shoulder_y`
- 肩-肘-手首角度:
  肘を頂点とする 3 点角度
- 手首の高さ時系列:
  左右手首の `y` 座標
- 胴体の傾き:
  両肩中点から両腰中点へのベクトルの鉛直からの角度

画像座標なので、`y` が小さいほど高い位置です。

## 注意点

- `whole_image` 前提なので、複数人物や人物が小さい動画では精度が落ちます。
- 初回実行時はモデル重みのダウンロードが入ります。
- Windows + GPU は PyTorch / CUDA / MMCV の組み合わせ依存が強いので、まず CPU で通すのが安全です。

## 改善候補

1. detector 付き推論に変更して人物切り出しを安定化
2. 時系列スムージング追加
3. 肩幅や体幹長で正規化
4. 弓道フェーズ検出
5. Streamlit 上で複数グラフの比較表示
6. 処理結果を ZIP で一括ダウンロード
