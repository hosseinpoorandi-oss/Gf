#!/usr/bin/env bash
# WinRescue ISO builder. Run as root on Debian bookworm (or in a debian:bookworm container).
# Output: ./WinRescue.iso
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Run as root:  sudo ./build.sh"; exit 1; }
if ! command -v lb >/dev/null; then
  command -v apt-get >/dev/null || { echo "Need Debian/Ubuntu (or use Docker, see README.md)"; exit 1; }
  apt-get update && apt-get install -y live-build debootstrap xorriso squashfs-tools ca-certificates
fi

WORK="$HERE/work"; rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK"

# Kernel parameters: NORMAL = safe GPU defaults, FAILSAFE = maximum compatibility.
# (nomodeset forces plain framebuffer graphics; our UI is simple so speed is irrelevant.)
BASE="boot=live components quiet loglevel=3 nomodeset modprobe.blacklist=nouveau video=vesafb:mtrr:3 vga=normal"
SAFE="boot=live components loglevel=7 nomodeset noapic nolapic acpi=off irqpoll modprobe.blacklist=nouveau nouveau.modeset=0 radeon.modeset=0 amdgpu.modeset=0 i915.modeset=0 video=vesafb:mtrr:3 vga=normal wr.mode=safe"

lb config \
  --distribution bookworm --architectures amd64 \
  --archive-areas "main contrib non-free non-free-firmware" \
  --binary-images iso-hybrid --bootloaders "syslinux,grub-efi" \
  --debian-installer none --memtest none \
  --iso-volume WINRESCUE --iso-application "WinRescue" --iso-publisher "WinRescue" \
  --bootappend-live "$BASE" \
  --bootappend-live-failsafe "$SAFE" \
  --apt-indices false --apt-recommends false

mkdir -p config/package-lists config/includes.chroot config/hooks/normal
cat > config/package-lists/winrescue.list.chroot <<'EOF'
live-boot live-config systemd-sysv linux-image-amd64 initramfs-tools
xserver-xorg-core xserver-xorg-video-all xserver-xorg-video-fbdev xserver-xorg-video-vesa
xserver-xorg-video-amdgpu xserver-xorg-video-ati xserver-xorg-video-nouveau
xserver-xorg-input-all xserver-xorg-input-libinput xserver-xorg-input-evdev
xinit x11-xserver-utils openbox libgl1-mesa-dri
python3 python3-gi gir1.2-gtk-3.0 fonts-dejavu-core adwaita-icon-theme
whiptail kbd
gdisk parted util-linux dosfstools ntfs-3g libhivex-bin efibootmgr e2fsprogs
firmware-linux-free firmware-linux-nonfree firmware-misc-nonfree firmware-amd-graphics
intel-microcode amd64-microcode
bash coreutils findutils gawk sed grep mount udev kmod procps
EOF

cp -a "$HERE/overlay/." config/includes.chroot/

cat > config/hooks/normal/0100-winrescue.hook.chroot <<'EOF'
#!/bin/sh
set -e
chmod +x /usr/local/bin/wr-core /usr/local/bin/wr-session /usr/local/bin/wr-launch /usr/local/bin/wr-tui
systemctl enable winrescue.service
systemctl mask getty@tty1.service
EOF
chmod +x config/hooks/normal/0100-winrescue.hook.chroot

# Boot menu: replaces the generated BIOS (isolinux) and UEFI (grub) menus with 3 entries.
# Defensive: if the layout is not what we expect, it leaves the stock menus (which already
# carry the safe parameters from --bootappend-live / --bootappend-live-failsafe).
cat > config/hooks/normal/0200-bootmenu.hook.binary <<'HOOKEOF'
#!/bin/sh
[ -d binary ] && cd binary
if [ ! -d live ]; then echo "WR: no live/ dir, menus left untouched"; exit 0; fi
K=$(ls live | grep '^vmlinuz' | head -n1); I=$(ls live | grep '^initrd' | head -n1)
[ -n "$K" ] && [ -n "$I" ] || { echo "WR: kernel/initrd not found, menus left untouched"; exit 0; }

BASE="boot=live components quiet loglevel=3 nomodeset modprobe.blacklist=nouveau video=vesafb:mtrr:3 vga=normal"
SAFE="boot=live components loglevel=7 nomodeset noapic nolapic acpi=off irqpoll modprobe.blacklist=nouveau nouveau.modeset=0 radeon.modeset=0 amdgpu.modeset=0 i915.modeset=0 video=vesafb:mtrr:3 vga=normal wr.mode=safe"
TEXT="$BASE wr.mode=text"

if [ -f isolinux/isolinux.cfg ]; then
  cp isolinux/isolinux.cfg isolinux/isolinux.cfg.orig
  cat > isolinux/isolinux.cfg <<EOF
UI vesamenu.c32
PROMPT 0
TIMEOUT 100
DEFAULT normal
MENU TITLE WinRescue - Windows Wipe and Repair
MENU MARGIN 8
MENU ROWS 6
MENU COLOR screen 0 #ffe5e7eb #ff0b1220 none
MENU COLOR border 0 #ff1f2a44 #00000000 none
MENU COLOR title 0 #ff38bdf8 #00000000 none
MENU COLOR unsel 0 #ffe5e7eb #00000000 none
MENU COLOR sel 0 #ff0b1220 #ff38bdf8 none
MENU COLOR hotkey 0 #fffbbf24 #00000000 none
MENU COLOR hotsel 0 #ff0b1220 #ff38bdf8 none
MENU COLOR tabmsg 0 #ff94a3b8 #00000000 none
MENU COLOR timeout_msg 0 #ff94a3b8 #00000000 none
MENU COLOR timeout 0 #fffbbf24 #00000000 none

LABEL normal
  MENU LABEL ^WinRescue  (Normal mode)
  LINUX /live/$K
  INITRD /live/$I
  APPEND $BASE

LABEL safe
  MENU LABEL ^Ultra Fail-Safe mode  (no ACPI/APIC, plain graphics)
  LINUX /live/$K
  INITRD /live/$I
  APPEND $SAFE

LABEL text
  MENU LABEL ^Text mode only  (no graphics at all)
  LINUX /live/$K
  INITRD /live/$I
  APPEND $TEXT
EOF
  echo "WR: isolinux menu written"
else echo "WR: isolinux.cfg not found"; fi

if [ -f boot/grub/grub.cfg ]; then
  cp boot/grub/grub.cfg boot/grub/grub.cfg.orig
  cat > boot/grub/grub.cfg <<EOF
search --no-floppy --file --set=root /live/$K
set default=0
set timeout=10
set menu_color_normal=light-gray/black
set menu_color_highlight=black/light-cyan

menuentry "WinRescue  (Normal mode)" {
  linux /live/$K $BASE
  initrd /live/$I
}
menuentry "Ultra Fail-Safe mode  (no ACPI/APIC, plain graphics)" {
  linux /live/$K $SAFE
  initrd /live/$I
}
menuentry "Text mode only  (no graphics at all)" {
  linux /live/$K $TEXT
  initrd /live/$I
}
EOF
  echo "WR: grub menu written"
else echo "WR: boot/grub/grub.cfg not found"; fi

echo "WR: boot layout:"; find . -maxdepth 3 -name '*.cfg' | sort
HOOKEOF
chmod +x config/hooks/normal/0200-bootmenu.hook.binary

lb build 2>&1 | tee "$HERE/build.log"

ISO="$(ls -1 ./*.iso | head -n1)"
cp "$ISO" "$HERE/WinRescue.iso"
( cd "$HERE" && sha256sum WinRescue.iso | tee WinRescue.iso.sha256 )
echo "Done -> $HERE/WinRescue.iso"
