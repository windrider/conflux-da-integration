# 使用官方 Rust 镜像作为构建环境
FROM rust:1.78 AS builder

WORKDIR /app

ENV CARGO_NET_GIT_FETCH_WITH_CLI=true

RUN apt-get update && apt-get install -y --no-install-recommends protobuf-compiler libclang-dev git ca-certificates && rm -rf /var/lib/apt/lists/*

RUN mkdir /build
COPY ./0g-da-node/dev_support/download_params.sh /build/download_params.sh
RUN cd /build && ./download_params.sh && cd /app

# Copy dependency manifests first to maximize layer cache hits.
COPY ./0g-da-node/Cargo.toml ./Cargo.toml
COPY ./0g-da-node/Cargo.lock ./Cargo.lock
COPY ./0g-da-node/grpc/Cargo.toml ./grpc/Cargo.toml
COPY ./0g-da-node/server/Cargo.toml ./server/Cargo.toml
COPY ./0g-da-node/contract-interface/Cargo.toml ./contract-interface/Cargo.toml
COPY ./0g-da-node/storage/Cargo.toml ./storage/Cargo.toml
COPY ./0g-da-node/chain-state/Cargo.toml ./chain-state/Cargo.toml
COPY ./0g-da-node/utils/Cargo.toml ./utils/Cargo.toml
COPY ./0g-da-node/client/Cargo.toml ./client/Cargo.toml
COPY ./0g-da-node/da-miner/Cargo.toml ./da-miner/Cargo.toml
COPY ./0g-da-node/chain-utils/Cargo.toml ./chain-utils/Cargo.toml
COPY ./0g-da-node/key-gen/Cargo.toml ./key-gen/Cargo.toml

# Cargo validates workspace members when resolving dependencies.
# Create minimal placeholder targets so `cargo fetch` works before full source copy.
RUN mkdir -p grpc/src server/src contract-interface/src storage/src chain-state/src utils/src client/src da-miner/src chain-utils/src key-gen/src \
    && printf 'fn main() {}\n' > grpc/src/main.rs \
    && printf 'fn main() {}\n' > server/src/main.rs \
    && printf 'pub fn _placeholder() {}\n' > contract-interface/src/lib.rs \
    && printf 'pub fn _placeholder() {}\n' > storage/src/lib.rs \
    && printf 'pub fn _placeholder() {}\n' > chain-state/src/lib.rs \
    && printf 'pub fn _placeholder() {}\n' > utils/src/lib.rs \
    && printf 'fn main() {}\n' > client/src/main.rs \
    && printf 'pub fn _placeholder() {}\n' > da-miner/src/lib.rs \
    && printf 'pub fn _placeholder() {}\n' > chain-utils/src/lib.rs \
    && printf 'fn main() {}\n' > key-gen/src/main.rs

RUN git config --global http.version HTTP/1.1 \
    && git config --global http.lowSpeedLimit 1000 \
    && git config --global http.lowSpeedTime 60

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    sh -c 'for i in 1 2 3 4 5; do cargo fetch --locked && exit 0; echo "cargo fetch failed ($i/5), retrying..."; sleep $((i*5)); done; exit 1'

COPY ./0g-da-node .

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/app/target \
    cargo build --locked --release -p server

RUN --mount=type=cache,target=/app/target cp /app/target/release/server ./server-output


FROM ubuntu:latest

RUN apt-get update \
    && apt-get install -y netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*  # 清除缓存以减小镜像大小

# 复制构建好的二进制文件到新的容器中
COPY --from=builder /app/server-output /usr/local/bin/server
COPY --from=builder /build/params ./params
COPY ./config.toml ./config.toml