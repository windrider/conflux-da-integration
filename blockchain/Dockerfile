FROM rust:1.75-slim AS builder

ENV CMAKE_POLICY_VERSION_MINIMUM="3.5"
ENV CFLAGS="-Wno-error=array-bounds -Wno-array-bounds"
ENV CXXFLAGS="-Wno-error=array-bounds -Wno-array-bounds"

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    clang \
    libclang-dev \
    libssl-dev \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Configure Cargo to use git CLI for better network compatibility
RUN mkdir -p /root/.cargo && \
    echo '[net]' > /root/.cargo/config.toml && \
    echo 'git-fetch-with-cli = true' >> /root/.cargo/config.toml && \
    echo '' >> /root/.cargo/config.toml && \
    echo '[source.crates-io]' >> /root/.cargo/config.toml && \
    echo 'replace-with = "ustc"' >> /root/.cargo/config.toml && \
    echo '' >> /root/.cargo/config.toml && \
    echo '[source.ustc]' >> /root/.cargo/config.toml && \
    echo 'registry = "https://mirrors.ustc.edu.cn/crates.io-index"' >> /root/.cargo/config.toml

# Copy Conflux source code
COPY ./conflux-rust .

# Build Conflux in release mode
RUN cargo build --release --bin conflux

# Build pos-genesis-tool for validator setup
RUN cargo build --release --bin pos-genesis-tool

# Final stage
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy binaries from builder
COPY --from=builder /build/target/release/conflux /usr/local/bin/conflux
COPY --from=builder /build/target/release/pos-genesis-tool /usr/local/bin/pos-genesis-tool

# Create directories
RUN mkdir -p /data /config

# Copy configuration and startup script
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Expose ports
# 8545: eSpace HTTP RPC
# 8546: eSpace WebSocket
# 12537: Core Space HTTP RPC
# 12535: P2P
EXPOSE 8545 8546 12537 12535

WORKDIR /data

CMD ["/start.sh"]