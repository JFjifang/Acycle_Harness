# 已完成排练：原始 MATLAB 图件与文件

这是已完成的真实排练结果，供检查和明确标注的回放。现场新计算按 [HANDOFF.zh-CN.md](HANDOFF.zh-CN.md) 启动，再上传原始数据和短提示。此次成功排练的科学原件包含在独立 Newark 演示包和完整研究包中；轻量本地 handoff 仅带安装材料与验收记录。首次失败尝试的完整科学原件另存完整研究包，其公开轨迹、错误与校验回执也保留在演示包中。

首轮六阶段主线加峰/谷相位比较共 8 次 MATLAB 运行，第二条独立用户消息再完成一次 eCOCO 窗口调整。两条消息来自同一 Session。GitHub 后端首轮用时 1413 秒，第二轮 228 秒；本地 MATLAB 耗时需在发布会机器预演。

讲解请使用 [经人工校核的口径](REVIEWED_NARRATIVE.zh-CN.md)。模型原文与问题清单保留在 [公开验收](../../validation/v0.5/public-harness/evaluation/fixedtransport-evaluation.md)，不能把下面图件当作已独立验证的 Newark 年代学。

以下链接指向包内 MATLAB 原件，不改变其数据或图像。

## 前处理与插值

运行 `20261025T105410Z-2d857a4092b0`。

![前处理与插值](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105410Z-2d857a4092b0/outputs/interpolation.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105410Z-2d857a4092b0/outputs/analysis.mat) · [interpolated.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105410Z-2d857a4092b0/outputs/interpolated.csv)

## 深度域频谱与演化谱

运行 `20261025T105716Z-dbf6eaaeabb0`。

![深度域频谱与演化谱](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105716Z-dbf6eaaeabb0/outputs/spectrum.png)

![深度域频谱与演化谱](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105716Z-dbf6eaaeabb0/outputs/evolution.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105716Z-dbf6eaaeabb0/outputs/analysis.mat) · [processed.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105716Z-dbf6eaaeabb0/outputs/processed.csv)

## COCO 与 eCOCO

运行 `20261025T105950Z-0531b1ec894c`。

![COCO 与 eCOCO](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105950Z-0531b1ec894c/outputs/coco_figure_1.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105950Z-0531b1ec894c/outputs/analysis.mat) · [coco.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T105950Z-0531b1ec894c/outputs/coco.csv)

## eCOCO 基线

运行 `20261025T110220Z-a5880602e02b`。

![eCOCO 基线](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110220Z-a5880602e02b/outputs/ecoco_figure_1.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110220Z-a5880602e02b/outputs/analysis.mat) · [ecoco.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110220Z-a5880602e02b/outputs/ecoco.csv) · [tracked_rate.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110220Z-a5880602e02b/outputs/tracked_rate.csv)

## 峰值控制点与相对时间轴

运行 `20261025T110455Z-2b96156ba364`。

![峰值控制点与相对时间轴](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110455Z-2b96156ba364/outputs/tuning.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110455Z-2b96156ba364/outputs/analysis.mat) · [age_model.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110455Z-2b96156ba364/outputs/age_model.csv) · [control_points.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110455Z-2b96156ba364/outputs/control_points.csv)

## 原始 proxy 的时间域诊断

运行 `20261025T110726Z-6e76718b431c`。

![原始 proxy 的时间域诊断](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110726Z-6e76718b431c/outputs/spectrum.png)

![原始 proxy 的时间域诊断](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110726Z-6e76718b431c/outputs/evolution.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110726Z-6e76718b431c/outputs/analysis.mat) · [age_model.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110726Z-6e76718b431c/outputs/age_model.csv) · [processed.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T110726Z-6e76718b431c/outputs/processed.csv)

## 追问后的 eCOCO 800 m / 200 m

运行 `20261025T112631Z-40fc9822b7b9`。

![追问后的 eCOCO 800 m / 200 m](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T112631Z-40fc9822b7b9/outputs/ecoco_figure_1.png)

原件：[analysis.mat](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T112631Z-40fc9822b7b9/outputs/analysis.mat) · [ecoco.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T112631Z-40fc9822b7b9/outputs/ecoco.csv) · [tracked_rate.csv](../../validation/v0.5/scientific-runs/fixedtransport/newark_relative_time_complete/20261025T112631Z-40fc9822b7b9/outputs/tracked_rate.csv)
