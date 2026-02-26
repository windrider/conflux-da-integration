# 使用官方 Rust 镜像作为构建环境
FROM rust:1.80 AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y protobuf-compiler libclang-dev

RUN rustup install 1.80

COPY ./0g-da-example-rust .

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    cargo fetch

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/app/target \
    cargo build --release

RUN --mount=type=cache,target=/app/target cp /app/target/release/zgdatestharness ./client-output


FROM ubuntu:latest

# 复制构建好的二进制文件到新的容器中
COPY --from=builder /app/client-output /usr/local/bin/client