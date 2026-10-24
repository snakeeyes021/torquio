# Source of Torquio's Wine engine

The Wine engine in `/opt/wine-custom` is Wine (GNU LGPL 2.1 or later; see `COPYING.LIB` in the source)
built from:

- `wine-source.tar.xz` (next to this file): the complete source it was compiled from, i.e.
  [zhiyi/wine](https://gitlab.winehq.org/zhiyi/wine) at the commit recorded in
  `/opt/wine-custom/share/torquio/build-info` with Torquio's patches applied.
- `patches/`: Torquio's patches on their own.

The build steps are `scripts/1-build/build_wine.sh` and `scripts/1-build/Containerfile` in
<https://github.com/snakeeyes021/torquio>.
