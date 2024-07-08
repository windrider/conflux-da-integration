# 使用官方 Rust 镜像作为构建环境
FROM rust:1.78 AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y protobuf-compiler libclang-dev

RUN rustup install 1.78
RUN rustup default 1.78
RUN rustup target add wasm32-unknown-unknown
RUN rustup component add rustfmt clippy rust-src

COPY ./0g-da-encoder .

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    cargo fetch

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/app/target \
    cargo build --release -p server --features grpc/parallel

RUN --mount=type=cache,target=/app/target cp /app/target/release/server ./server-output


FROM ubuntu:latest

# 复制构建好的二进制文件到新的容器中
COPY --from=builder /app/server-output /usr/local/bin/server
COPY --from=builder /app/run/config.toml ./config.toml