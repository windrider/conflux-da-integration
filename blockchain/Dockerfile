FROM golang:1.21-alpine AS build-env

# Set up dependencies
# bash, jq, curl for debugging
# git, make for installation
# libc-dev, gcc, linux-headers, eudev-dev are used for cgo and ledger installation
RUN apk add bash git make libc-dev gcc linux-headers eudev-dev jq curl

# Set working directory for the build
WORKDIR /root
# default home directory is /root

# Copy dependency files first to facilitate dependency caching
COPY ./0g-chain/go.mod ./
COPY ./0g-chain/go.sum ./

# Download dependencies
RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg/mod \
    go version && go mod download

# Add source files
COPY ./0g-chain .

RUN sed -i 's|EpochBlocks:       5760|EpochBlocks:       10|' x/dasigners/v1/types/genesis.go

#ENV LEDGER_ENABLED False

# Mount go build and mod caches as container caches, persisted between builder invocations
RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg/mod \
    make install

FROM alpine:3.15

RUN apk add bash jq curl
COPY --from=build-env /go/bin/0gchaind /0gchaind
COPY --from=build-env /root/localtestnet.sh /localtestnet.sh

RUN sed -i 's|BINARY=./out/$NATIVE_GO_OS/0gchaind|BINARY=/0gchaind|' localtestnet.sh
RUN sed -i 's|\(\$BINARY start --home \$DATA\)|\1 --json-rpc.address 0.0.0.0:8545|' localtestnet.sh
RUN echo 'curl -X POST --data '"'"'{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'"'"' -H "Content-Type: application/json" http://localhost:8545' > checkhealth.sh

CMD ["/bin/bash", "-c", "./localtestnet.sh 2>/dev/null"]