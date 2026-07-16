#!/bin/bash
# Build Conflux from blockchain/conflux-rust (branch da-signers-solidity = upstream/master).
# Output binaries are copied to blockchain/ for Docker (see Dockerfile).
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/conflux-rust"

BRANCH="$(git branch --show-current)"
echo "Building conflux-rust on branch: $BRANCH"
echo "Expected: da-signers-solidity (no built-in da.rs)"

# Avoid miniconda CMake 4.x breaking rocksdb/titan configure; use system cmake 3.28.
if [ -x /usr/bin/cmake ]; then
    export PATH="/usr/bin:$PATH"
    echo "Using $(cmake --version | head -1)"
fi

# rocksdb/titan enables -Werror; GCC 12/13 may hit false-positive array-bounds in titan.
export CXXFLAGS="${CXXFLAGS:--Wno-error=array-bounds -Wno-array-bounds}"
export CMAKE_CXX_FLAGS="${CMAKE_CXX_FLAGS:-$CXXFLAGS}"
echo "CXXFLAGS=$CXXFLAGS"

if command -v g++-12 >/dev/null 2>&1; then
    export CC=gcc-12
    export CXX=g++-12
    echo "Using $CC / $CXX"
fi

# Clear stale rocksdb/titan cmake cache when flags or CC/CXX change.
rm -rf target/release/build/librocksdb_sys-* target/release/build/libtitan_sys-* 2>/dev/null || true

cargo build --release -p conflux

cp -f target/release/conflux "$ROOT/conflux"
if [ -f target/release/pos-genesis-tool ]; then
    cp -f target/release/pos-genesis-tool "$ROOT/pos-genesis-tool"
fi

echo "Done. Binaries:"
ls -lh "$ROOT/conflux" "$ROOT/pos-genesis-tool" 2>/dev/null || ls -lh "$ROOT/conflux"
