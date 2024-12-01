# bilibili-rss

B站（bilibili）RSS源生成服务。在部署完毕后，你可以通过访问该服务的地址；来订阅B站的RSS源。

例如，你可以订阅 `https://you-domain.com/bilibili/dynamic/32708462` 这个地址来获取该用户的动态。

## 已实现接口

### 无需登录

- 用户动态：/bilibili/dynamic/{user_id}

### 需登录

- 

## 部署方式

### Docker部署（推荐）

```shell
git clone https://github.com/VIILing/bilibili-rss.git
cd bilibili-rss
commitId=$(git rev-parse --short HEAD)
sudo docker build -t VIILing/bilibili-rss:$commitId -t VIILing/bilibili-rss:latest .
sudo docker compose up -d
```

### 手动部署

手动部署需预先安装`python3.10`环境。

```shell
git clone https://github.com/VIILing/bilibili-rss.git
cd bilibili-rss
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cd src
fastapi run main.py
```
