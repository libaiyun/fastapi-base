# 容器化部署

```shell
docker build -t fastapi-base:1.0 .

docker run -d --name fastapi-base \
-p 8150:8150 \
-e APP_ENV=prod \
-e SERVER_HOST=192.168.98.79 \
-e SERVER_PORT=8150 \
-v $(pwd)/config-prod.yaml:/app/config-prod.yaml \
-v $(pwd)/log:/app/log
fastapi-base:1.0
```

Windows CMD下容器启动命令:

```cmd
docker build -t fastapi-base:1.0 .

docker run -d --name fastapi-base ^
-p 8150:8150 ^
-e APP_ENV=dev ^
-e SERVER_HOST=192.168.20.73 ^
-e SERVER_PORT=8150 ^
-v "%CD%\config-dev.yaml:/app/config-dev.yaml" ^
-v "%CD%\log:/app/log" ^
fastapi-base:1.0
```

ORM模型生成:

```bash
sqlacodegen --generator sqlmodels mysql+pymysql://user:passwd@host:port/db --outdir app/models --options remove_prefix --exclude-pattern "_copy$"
```
