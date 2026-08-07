# SPDX-License-Identifier: GPL-2.0-only
# SPDX-FileCopyrightText: Copyright (c) 2023-2025, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.

DTC_FLAGS += -@

old-dtb := $(dtb-y)
old-dtbo := $(dtbo-y)
dtb-y :=
dtbo-y :=
makefile-path := t23x/nv-public/overlay

# JP7.2 official Orin Nano package targets.
dtbo-y += tegra234-p3767-camera-p3768-tevs-dual-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls3.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync-external-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel-fsync-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-fsync-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-fsync-external-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-tunnel-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-tunnel-fsync-overlay.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vlm-gm2-ext-io-overlay.dtbo
dtbo-y += tegra234-p3737-camera-vls-gm2-overlay.dtbo
dtbo-y += tegra234-p3737-camera-vls-gm2-fsync-overlay.dtbo
dtbo-y += tegra234-p3737-camera-vls-gm2-fsync-external-overlay.dtbo
dtbo-y += tegra234-p3737-camera-vls-gm2-tunnel-overlay.dtbo
dtbo-y += tegra234-p3737-camera-vls-gm2-tunnel-fsync-overlay.dtbo

ifneq ($(dtb-y),)
dtb-y := $(addprefix $(makefile-path)/,$(dtb-y))
endif
ifneq ($(dtbo-y),)
dtbo-y := $(addprefix $(makefile-path)/,$(dtbo-y))
endif

dtb-y += $(old-dtb)
dtbo-y += $(old-dtbo)
