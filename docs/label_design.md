# 弓道射型評価用 ラベル設計書 v0.1

## 目的

本設計書は、弓道動画から射型評価を行う特化型 AI を構築するための教師データ仕様を定義する。

このラベル設計の用途は以下の 3 つである。

1. ルールベース評価の基準整理
2. 教師あり学習用データセットの作成
3. モバイルアプリ上の評価表示項目の統一

本設計書では、まず横動画・単一人物・1 射単位を前提とする。

## 設計方針

- 最初は動画全体ラベルと八節ラベルを優先する
- いきなり細かいフレーム単位評価を要求しない
- 指導者が実際に見ている観点に近い単位でラベル化する
- 将来の機械学習に使えるよう、数値・カテゴリ・複数選択タグを分けて定義する
- 後からラベル定義を拡張できるように、列名は安定した英字キーにする

## ラベル単位

ラベルは次の 3 層で管理する。

1. 動画単位ラベル
2. 八節またはフェーズ単位ラベル
3. 問題タグ・コメントラベル

## 1. 動画単位ラベル

1 射全体を対象に付与するラベル。

| 列名 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `video_id` | string | 必須 | 動画の一意 ID |
| `subject_id` | string | 必須 | 被験者 ID |
| `session_id` | string | 任意 | 撮影セッション ID |
| `shot_id` | string | 任意 | 1 射単位 ID |
| `camera_view` | category | 必須 | 基本は `side` |
| `handedness` | category | 必須 | `right` / `left` |
| `experience_level` | category | 必須 | `beginner` / `intermediate` / `advanced` / `instructor` |
| `usable_for_training` | bool | 必須 | 学習利用可否 |
| `overall_score` | int | 必須 | 総合点 0-100 |
| `overall_grade` | category | 必須 | `A` / `B` / `C` / `D` / `E` |
| `stability_score` | int | 任意 | 全体安定性 0-100 |
| `form_consistency_score` | int | 任意 | 射型一貫性 0-100 |
| `release_quality_score` | int | 任意 | 離れの質 0-100 |
| `zanshin_quality_score` | int | 任意 | 残心の質 0-100 |
| `primary_issue` | category | 任意 | 最も大きな問題点 |
| `secondary_issue` | category | 任意 | 2 番目に大きな問題点 |
| `free_comment` | text | 任意 | 自由記述コメント |
| `annotator_id` | string | 必須 | 評価者 ID |
| `annotation_confidence` | int | 任意 | 評価者の確信度 1-5 |

## 2. 八節単位ラベル

八節または動作フェーズごとに付与するラベル。

対象フェーズ:

- `ashibumi`
- `dozukuri`
- `yugamae`
- `uchiokoshi`
- `hikiwake`
- `kai`
- `hanare`
- `zanshin`

### 八節ラベル共通項目

| 列名 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `video_id` | string | 必須 | 動画 ID |
| `phase_name` | category | 必須 | 八節名 |
| `phase_score` | int | 必須 | フェーズ点 0-100 |
| `phase_grade` | category | 必須 | `A` / `B` / `C` / `D` / `E` |
| `phase_start_sec` | float | 任意 | 開始時刻 |
| `phase_end_sec` | float | 任意 | 終了時刻 |
| `phase_stability_score` | int | 任意 | 安定性評価 0-100 |
| `phase_comment` | text | 任意 | フェーズ単位コメント |

## 3. 問題タグ

複数選択可能な教師タグ。最初は動画単位で付け、余力があればフェーズ単位にも付ける。

### 3-1. 全体問題タグ

| タグ名 | 意味 |
|---|---|
| `shoulder_raised` | 肩が上がっている |
| `shoulder_unlevel` | 左右肩の高さ差が大きい |
| `torso_lean_left` | 胴体が左へ傾く |
| `torso_lean_right` | 胴体が右へ傾く |
| `left_right_asymmetry` | 左右差が大きい |
| `wrist_height_unstable` | 手首高さが不安定 |
| `elbow_line_bad` | 肘の収まりやラインが悪い |
| `release_unstable` | 離れが不安定 |
| `zanshin_collapsed` | 残心が崩れる |
| `motion_inconsistent` | 動作全体の一貫性が低い |

### 3-2. フェーズ別推奨タグ

#### 足踏み

- `ashibumi_width_bad`
- `ashibumi_alignment_bad`

#### 胴造り

- `dozukuri_torso_tilt`
- `dozukuri_head_alignment_bad`
- `dozukuri_shoulder_tension`

#### 弓構え

- `yugamae_hand_position_bad`
- `yugamae_balance_bad`

#### 打起し

- `uchiokoshi_shoulder_lift`
- `uchiokoshi_arm_path_bad`
- `uchiokoshi_wrist_height_bad`

#### 引分け

- `hikiwake_elbow_path_bad`
- `hikiwake_torso_shift`
- `hikiwake_left_right_unbalance`

#### 会

- `kai_too_short`
- `kai_unstable`
- `kai_shoulder_tension`
- `kai_wrist_height_bad`

#### 離れ

- `hanare_release_direction_bad`
- `hanare_body_collapse`
- `hanare_timing_bad`

#### 残心

- `zanshin_posture_collapse`
- `zanshin_balance_bad`
- `zanshin_arm_line_bad`

## 4. 総合評価スケール

総合評価は 0-100 点を基本とし、表示用に A-E を併用する。

| Grade | Score Range | 意味 |
|---|---:|---|
| A | 90-100 | 非常に良い |
| B | 75-89 | 良い |
| C | 60-74 | おおむね許容 |
| D | 40-59 | 改善が必要 |
| E | 0-39 | 大きな改善が必要 |

## 5. ラベル付与の優先順位

最初のデータ収集では、以下を最低限必須とする。

### 最低限必須

- `video_id`
- `subject_id`
- `camera_view`
- `handedness`
- `experience_level`
- `overall_score`
- `overall_grade`
- `primary_issue`
- `annotator_id`

### 推奨

- 八節ごとの `phase_score`
- 問題タグ複数選択
- `free_comment`

### 余力があれば

- `phase_start_sec`
- `phase_end_sec`
- 詳細なフェーズタグ
- 複数評価者による重複ラベル

## 6. 評価者運用ルール

- 1 動画につき最低 1 名の評価者を付ける
- 重要動画は 2 名以上で重複評価する
- 評価者ごとのばらつきを確認するため、`annotator_id` を必ず保持する
- 明らかに評価不能な動画は `usable_for_training=false` とする

## 7. 学習用データとしての推奨量

### PoC 段階

- 50-100 本
- 総合評価 + 主問題タグ

### 初期実用段階

- 100-300 本
- 総合評価 + 八節評価 + 問題タグ

### 実用化を見据える段階

- 300-1000 本
- 複数レベル、複数被験者、複数評価者

重要なのは本数だけでなく、以下の分布を揃えること。

- 被験者のレベル差
- 体格差
- 崩れ方の種類
- 撮影日の違い
- 同一人物への偏りを抑えること

## 8. CSV 例

### 動画単位ラベル CSV

```text
video_id,subject_id,session_id,shot_id,camera_view,handedness,experience_level,usable_for_training,overall_score,overall_grade,stability_score,form_consistency_score,release_quality_score,zanshin_quality_score,primary_issue,secondary_issue,free_comment,annotator_id,annotation_confidence
vid_0001,subj_01,sess_01,shot_01,side,right,beginner,true,62,C,58,60,55,63,shoulder_unlevel,wrist_height_unstable,"会で肩に力みが見られる",coach_01,4
```

### フェーズ単位ラベル CSV

```text
video_id,phase_name,phase_score,phase_grade,phase_start_sec,phase_end_sec,phase_stability_score,phase_comment
vid_0001,uchiokoshi,58,C,1.20,2.10,55,"打起しで肩が上がる"
vid_0001,hikiwake,61,C,2.10,3.90,60,"引分けで左右差が出る"
```

## 9. 今後の拡張

将来は次を追加できる。

- フレーム単位イベントラベル
- 連続時系列スコア
- 射ごとの改善提案テンプレート
- 的中有無や矢所情報
- 主観評価と客観指標の分離

## 10. 次にやること

本設計書の次は以下を作る。

1. 特徴量設計書
2. ルールベース評価仕様
3. ラベル付与ガイドライン
4. 評価用 CSV テンプレート
