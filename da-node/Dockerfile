# 使用官方 Rust 镜像作为构建环境
FROM rust:1.78 AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y protobuf-compiler libclang-dev

RUN rustup install 1.78
RUN rustup default 1.78
RUN rustup target add wasm32-unknown-unknown
RUN rustup component add rustfmt clippy rust-src

RUN mkdir /build
COPY ./0g-da-node/dev_support/download_params.sh /build/download_params.sh
RUN cd /build && ./download_params.sh && cd /app

COPY ./0g-da-node .

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    cargo fetch

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/app/target \
    cargo build --release -p server

RUN --mount=type=cache,target=/app/target cp /app/target/release/server ./server-output


FROM ubuntu:latest

RUN apt-get update \
    && apt-get install -y netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*  # 清除缓存以减小镜像大小

# 复制构建好的二进制文件到新的容器中
COPY --from=builder /app/server-output /usr/local/bin/server
COPY --from=builder /build/params ./params
COPY ./config.toml ./config.toml
RUN sed -i \
  -e 's|eth_rpc_endpoint = "https://rpc-testnet.0g.ai"|eth_rpc_endpoint = "http://0g-chain:8545/"|' \
  -e 's|socket_address = "<public_ip/dns>:34000"|socket_address = "0g-da-node:34000"|' \
  -e 's|da_entrance_address = ""|da_entrance_address = "0x64fcfde2350E08E7BaDc18771a7674FAb5E137a2"|' \
  -e 's|signer_bls_private_key = ""|signer_bls_private_key = "11"|' \
  -e 's|signer_eth_private_key = ""|signer_eth_private_key = "0x17939f5b4fa643ab86df3ae9d0b8f9c8c0c14328e679ece6c243d32dab673e49"|' \
  -e 's|enable_das = "false"|enable_das = "true"|' \
  ./config.toml
