FROM golang:1.21-alpine AS builder

# Set up dependencies
# bash, jq, curl for debugging
# git, make for installation
# libc-dev, gcc, linux-headers, eudev-dev are used for cgo and ledger installation
RUN apk add bash git make libc-dev gcc linux-headers eudev-dev jq curl

WORKDIR /app

RUN mkdir ./api
COPY ./0g-da-client/go.mod ./
COPY ./0g-da-client/go.sum ./
COPY ./0g-da-client/api/go.mod ./api
COPY ./0g-da-client/api/go.mod ./api

# Download dependencies
RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg/mod \
    go env -w GOPROXY=https://goproxy.cn,direct && \
    go version && go mod download

COPY ./0g-da-client .

RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg/mod \
    cd disperser && make build_combined && cd ..

FROM alpine:3.15

RUN apk add bash jq curl

COPY --from=builder /app/disperser/bin/combined combined
RUN mkdir /data
