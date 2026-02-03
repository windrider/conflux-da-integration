# Use pre-built binaries from local compilation
# Build locally first: cd conflux-rust && cargo build --release
FROM ubuntu:24.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3t64 \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built binaries (copy from conflux-da-integration before building)
COPY ./conflux /usr/local/bin/conflux
COPY ./pos-genesis-tool /usr/local/bin/pos-genesis-tool

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