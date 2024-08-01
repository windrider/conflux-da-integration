# 使用 Node.js 的官方基础镜像
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /builder

# 复制 package.json 和 yarn.lock 文件
COPY ./0g-da-contract/package.json ./0g-da-contract/yarn.lock ./

# 安装依赖，利用 Docker 层缓存
RUN --mount=type=cache,target=/builder/node_modules yarn install --frozen-lockfile

# 复制项目文件
COPY ./0g-da-contract .

RUN du -sh *

RUN sed -i '/await (await entrance_.initialize()).wait();/a\    await entrance_.setSamplePeriod(10);' src/deploy/deploy_da_entrance.ts

# 构建应用
RUN --mount=type=cache,target=/builder/node_modules yarn build

RUN mkdir /out
RUN --mount=type=cache,target=/builder/node_modules cp -r /builder/node_modules /out/node_modules

# 使用另一个干净的阶段来准备最终镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

RUN apk add bash

# 从构建器阶段复制构建的输出文件
COPY --from=builder /out/node_modules ./node_modules
COPY --from=builder /builder/build ./build
COPY --from=builder /builder/typechain-types ./typechain-types
COPY --from=builder /builder/contracts ./contracts
COPY --from=builder /builder/src ./src
COPY ./0g-da-contract/package.json ./
COPY ./0g-da-contract/hardhat.config.ts ./

RUN echo 'DEPLOYER_KEY = "17939f5b4fa643ab86df3ae9d0b8f9c8c0c14328e679ece6c243d32dab673e49"' > .env
RUN sed -i "s|http://0.0.0.0:8545|http://0g-chain:8545|" hardhat.config.ts