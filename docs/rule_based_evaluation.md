# 弓道射型評価用 ルールベース評価仕様 v0.1

## 目的

本仕様書は、弓道動画の射型評価を機械学習に依存せず実施するための、初期ルールベース評価方式を定義する。

本仕様の役割は以下。

1. 教師データが少ない段階でも一定の評価を可能にする
2. 特徴量設計とラベル設計を評価ロジックへ接続する
3. 将来の教師あり学習モデルのベースラインとする

## 基本方針

- 評価観点は弓道教本の内容にできる限り沿う
- 最初は横動画・単一人物・1 射単位で成立するルールに絞る
- ルールは「総合評価」「八節評価」「問題タグ判定」の 3 層に分ける
- 数値指標だけでなく、安定性・左右差・軌道も評価する
- 人体だけでなく、矢線・弓・本弭・末弭・地面基準を利用する

## 想定入力

本仕様で使用する入力は、以下のいずれかまたは組み合わせ。

1. 人体特徴量
2. 弓具特徴量
3. 基準線特徴量
4. フェーズ分割情報

参照元:

- [`docs/feature_design.md`](/mnt/c/Users/nanin/kyudo_pose/docs/feature_design.md)
- [`docs/label_design.md`](/mnt/c/Users/nanin/kyudo_pose/docs/label_design.md)

## 出力

### 1. 総合出力

- `overall_score`
- `overall_grade`
- `primary_issue`
- `secondary_issue`
- `auto_comment`

### 2. フェーズ出力

- 各八節の `phase_score`
- 各八節の `phase_grade`
- `phase_issue_tags`

### 3. 問題タグ

- `shoulder_unlevel`
- `torso_lean_left`
- `torso_lean_right`
- `wrist_height_unstable`
- `elbow_line_bad`
- `release_unstable`
- `zanshin_collapsed`
- 弓具関連タグ

## 評価ロジックの構造

ルールベース評価は 3 段階で行う。

1. フレーム単位判定
2. フェーズ単位集約
3. 動画単位総合評価

### 1. フレーム単位判定

各フレームで以下を計算する。

- 肩高さ差
- 胴体傾き
- 左右肘角度
- 左右手首高さ差
- 矢線角度
- 弓の垂直性
- 本弭・末弭の鉛直軌道偏差

### 2. フェーズ単位集約

フェーズごとに以下を集約する。

- 平均値
- 最大偏差
- 分散
- 安定度

### 3. 動画単位総合評価

フェーズ評価と重要特徴量の加重平均で総合点を出す。

## 評価スコアの基本設計

### スコアレンジ

- 各評価は 0-100 点
- 表示は A-E に変換

| Grade | Score Range |
|---|---:|
| A | 90-100 |
| B | 75-89 |
| C | 60-74 |
| D | 40-59 |
| E | 0-39 |

### 初期重み

総合評価の初期重み案:

| 項目 | 重み |
|---|---:|
| 胴造り | 0.15 |
| 打起し | 0.10 |
| 引分け | 0.15 |
| 会 | 0.20 |
| 離れ | 0.20 |
| 残心 | 0.10 |
| 全体安定性 | 0.10 |

足踏み、弓構えは初期版では補助評価扱いとし、後から重み調整する。

## 八節別評価ルール

## 1. 足踏み

### 主観点

- 足幅の適正
- 左右バランス
- 地面基準との整合

### 初期ルール

- 体幹の左右傾きが大きい場合減点
- 肩線と腰線の傾き差が大きい場合減点

### 主タグ候補

- `ashibumi_width_bad`
- `ashibumi_alignment_bad`

## 2. 胴造り

### 主観点

- 胴体の垂直性
- 肩の水平
- 頭部と体幹の整合

### 使用特徴量

- `torso_vertical_diff_deg`
- `shoulder_height_diff`
- `head_tilt_deg`
- `torso_tilt_var`

### 初期ルール

- 胴体の鉛直差が小さいほど高評価
- 左右肩高さ差が小さいほど高評価
- 頭部傾きと胴体傾きの差が大きい場合減点
- 胴体の揺れが大きい場合減点

### 主タグ候補

- `dozukuri_torso_tilt`
- `dozukuri_head_alignment_bad`
- `shoulder_unlevel`

## 3. 弓構え

### 主観点

- 手の位置関係
- 左右差
- 初期姿勢の安定性

### 使用特徴量

- `wrist_height_diff`
- `elbow_height_diff`
- `shoulder_height_diff`

### 初期ルール

- 手首高さ差が過大なら減点
- 肘高さ差が過大なら減点
- 姿勢が安定していない場合減点

## 4. 打起し

### 主観点

- 肩を上げすぎない
- 矢線が不自然に傾かない
- 上肢軌道が滑らか

### 使用特徴量

- `shoulder_height_diff`
- `left_wrist_y`
- `right_wrist_y`
- `arrow_angle_deg`
- `wrist_vertical_velocity`

### 初期ルール

- 打起し中に肩が持ち上がりすぎる場合減点
- 矢線角度の変化が不自然に大きい場合減点
- 手首高さの左右差が拡大する場合減点

### 主タグ候補

- `uchiokoshi_shoulder_lift`
- `uchiokoshi_arm_path_bad`
- `uchiokoshi_wrist_height_bad`

## 5. 引分け

### 主観点

- 肘の収まり
- 左右の均衡
- 胴体の流れがない
- 矢線が安定している

### 使用特徴量

- `left_elbow_angle_deg`
- `right_elbow_angle_deg`
- `elbow_height_diff`
- `torso_tilt_deg`
- `arrow_angle_deg`
- `arrow_angle_var`

### 初期ルール

- 左右肘角度差が大きい場合減点
- 肘高さ差が大きい場合減点
- 引分け中に胴体傾きが増加する場合減点
- 矢線の揺れが大きい場合減点

### 主タグ候補

- `hikiwake_elbow_path_bad`
- `hikiwake_torso_shift`
- `hikiwake_left_right_unbalance`

## 6. 会

### 主観点

- 静止性
- 肩の力みの少なさ
- 左右均衡
- 矢線と弓の安定

### 使用特徴量

- `kai_stillness_score`
- `shoulder_height_var`
- `torso_tilt_var`
- `arrow_angle_var`
- `bow_angle_var`
- `wrist_sway_px`

### 初期ルール

- 会の静止度が高いほど高評価
- 肩高さ差の分散が大きい場合減点
- 胴体傾き分散が大きい場合減点
- 矢線角度の分散が大きい場合減点
- 手首の揺れが大きい場合減点

### 主タグ候補

- `kai_unstable`
- `kai_shoulder_tension`
- `kai_wrist_height_bad`
- `kai_too_short`

## 7. 離れ

### 主観点

- 体の崩れが少ない
- 矢線が乱れない
- 離れ直前の静止から自然に移行する

### 使用特徴量

- `pre_release_stability`
- `arrow_angle_velocity`
- `torso_tilt_velocity`
- `release_quality_score` 相当の複合指標

### 初期ルール

- 離れ直前の揺れが大きい場合減点
- 離れで胴体が急激に崩れる場合減点
- 矢線が大きく乱れる場合減点

### 主タグ候補

- `release_unstable`
- `hanare_body_collapse`
- `hanare_timing_bad`

## 8. 残心

### 主観点

- 姿勢の保持
- 体幹の安定
- 弓手・妻手の線の維持

### 使用特徴量

- `zanshin_stability_score`
- `torso_tilt_var`
- `bow_angle_var`
- `motohazu_lateral_sway`
- `urahazu_lateral_sway`

### 初期ルール

- 残心中の体幹揺れが小さいほど高評価
- 弓や弭の横ぶれが大きい場合減点
- 残心で姿勢が崩れる場合大きく減点

### 主タグ候補

- `zanshin_collapsed`
- `zanshin_balance_bad`
- `zanshin_arm_line_bad`

## 弓具ルール

人体評価とは別に、弓具に対して独立したルールを置く。

## 1. 矢線

### 観点

- 矢線の角度
- 矢線のブレ
- 矢線と肩線の整合

### ルール

- `arrow_angle_var` が大きい場合減点
- `arrow_shoulder_angle_diff` が大きい場合減点
- フェーズごとに想定範囲外の角度なら減点

## 2. 弓の傾き

### 観点

- 弓全体が不必要に傾かない
- 引分け・会・残心で安定している

### ルール

- `bow_vertical_diff_deg` が大きい場合減点
- `bow_angle_var` が大きい場合減点

## 3. 本弭・末弭

### 観点

- 地面に対して鉛直に近い軌道で収まるか
- 横ぶれが少ないか

### ルール

- `motohazu_vertical_track_error` が大きい場合減点
- `urahazu_vertical_track_error` が大きい場合減点
- `motohazu_lateral_sway` が大きい場合減点
- `urahazu_lateral_sway` が大きい場合減点

これは将来、弓道教本の本文や指導者意見に照らして閾値を詰める。

## 減点方式の初期案

初期版は加点式ではなく減点式が扱いやすい。

### 例

- 基本点 100 点
- 各ルール違反に応じて減点
- 致命的崩れは大きく減点
- 軽微な乱れは小さく減点

### 例: 会フェーズ

- 会時間不足: -10
- 胩高さ差分散大: -8
- 矢線分散大: -10
- 手首揺れ大: -7

フェーズ点を出した後、総合点に加重合成する。

## 自動コメント生成方針

ルールベースではコメントもテンプレート生成する。

### 例

- `shoulder_unlevel` が強い:
  - 「左右の肩の高さ差が大きく、胴造りの安定性に課題があります。」
- `kai_unstable` が強い:
  - 「会での静止性が不足し、矢線と上体の安定が十分ではありません。」
- `motohazu_vertical_track_error` が大きい:
  - 「本弭の軌道に横ぶれが見られ、鉛直方向の収まりに課題があります。」

## 閾値の扱い

現段階では、厳密な固定閾値はまだ置かない。

まずは次の方法で決める。

1. 既存動画で特徴量分布を観察
2. 指導者の感覚と照合
3. 仮閾値を設定
4. ラベル付き動画で再調整

したがって v0.1 は「ルール項目の定義」であり、閾値確定版ではない。

## v0.1 で先に実装すべきルール

最初の実装対象は以下。

1. 左右肩高さ差
2. 胴体傾き
3. 左右肘角度
4. 左右手首高さ差
5. 会の静止度
6. 矢線角度
7. 矢線安定性
8. 残心安定度

弓・弭は次段階で追加する。

## 今後の拡張

- 教本本文との対応表作成
- 各ルールの閾値表作成
- 指導者ごとの差異管理
- ルールベースと機械学習評価のハイブリッド化

## 次にやること

1. ラベル付与ガイドライン
2. 閾値検討用の分析ノート
3. 今の Python アプリへのルールベース評価仮実装
