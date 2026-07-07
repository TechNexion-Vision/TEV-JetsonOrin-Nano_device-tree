# SPDX-License-Identifier: GPL-2.0-only
# SPDX-FileCopyrightText: Copyright (c) 2023-2025, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.

DTC_FLAGS += -@

old-dtb := $(dtb-y)
old-dtbo := $(dtbo-y)
dtb-y :=
dtbo-y :=
makefile-path := t23x/nv-public/overlay

# JP7.2 first-pass validation is intentionally limited to Orin Nano P3768
# TEVS direct and VLS-GM2/GMSL overlays. Restore broader overlay targets after
# the P3768 camera bring-up is proven on Jetson Linux r39.2.
dtbo-y += tegra234-p3767-camera-p3768-tevs-dual.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync-external.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel-fsync.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-new.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync-new.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-fsync-external-new.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel-new.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-tunnel-fsync-new.dtbo
dtbo-y += tegra234-p3767-camera-p3768-vls-gm2-ext-io-new.dtbo

ifneq ($(dtb-y),)
dtb-y := $(addprefix $(makefile-path)/,$(dtb-y))
endif
ifneq ($(dtbo-y),)
dtbo-y := $(addprefix $(makefile-path)/,$(dtbo-y))
endif

dtb-y += $(old-dtb)
dtbo-y += $(old-dtbo)
