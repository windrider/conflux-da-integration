#!/bin/bash

set -e

#!/bin/bash

# 检查环境变量yyy是否设置
if [[ -n $BUILD_PROXY ]]; then
    ARGS=(--build-arg HTTP_PROXY="$BUILD_PROXY" --build-arg HTTPS_PROXY="$BUILD_PROXY")
else
    ARGS=()
fi

if [[ $DOCKER_DEBUG -eq 1 ]]; then
    # 如果DOCKER_DEBUG是1，添加--progress=plain到ARGS数组
    ARGS+=(--progress=plain)
fi

echo "ARGS: ${ARGS[@]}"

cd blockchain
docker build -t 0g-chain ${ARGS[@]} .
cd ..

cd da-contract
docker build -t 0g-da-contract ${ARGS[@]} .
cd ..


cd da-node
docker build -t 0g-da-node ${ARGS[@]} .
cd ..

cd da-encoder
./0g-da-encoder/dev_support/download_params.sh
./0g-da-encoder/dev_support/check_cuda.sh || true
if [ $? -eq 0 ]; then
    cd ./0g-da-encoder
    cargo build --release -p server --features grpc/parallel,grpc/cuda
    cp ./target/release/server ..
    cd ..
    docker build -f Dockerfile-cuda -t 0g-da-encoder ${ARGS[@]} .
else
    docker build -t 0g-da-encoder ${ARGS[@]} .
fi
cd ..

cd da-disperser
docker build -t 0g-da-disperser ${ARGS[@]} .
cd ..

cd test-client
docker build -t 0g-da-test-client ${ARGS[@]} .
cd ..
