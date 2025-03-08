# 주식시세 모니터 (feat 한국투자증권 openapi)


### Introduction
본 프로젝트는 시스템트레이딩 프로젝트의 첫번째 단계로써, 관심종목 주식시세를 가져와 저장하고 시각화 하여 인사이트를 얻는것을 목적으로 합니다.

주식시세 그래프로 얻을수 있을 것으로 기대하는 인사이트
- 상승세, 하락세, 횡보 등 주가의 전반적인 움직임 확인
- 주가가 특정 수준에서 반등하거나 정체되는 패턴 발견
- 변동성 측정
- 가격 변동 및 거래량 확인
- 정기적으로 반복되는 패턴이 있는지 확인
- 공시, 뉴스 전후의 가격 변화 모니터

### Requirements
#### API Credential
본 프로젝트에서는 한국투자증권 openapi를 사용하였습니다. api호출을 위해 회원가입 및 api 접근권한을 획득하여야 합니다.

#### Data Store
api를 통해 가져온 정보는 influxdb에 저장합니다.

homelab에 구성된 k8s에 설치 하였고, NodePort 서비스를 이용해 접근하도록 설정하였습니다.
배포후 NodePort 서비스에 웹브라우저로 접근하여 초기 설정을 진행합니다. 

influxdb_deployment.yml
```
---
apiVersion: v1
kind: Namespace
metadata:
    name: influxdb
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
    labels:
        app: influxdb
    name: influxdb
    namespace: influxdb
spec:
    replicas: 1
    selector:
        matchLabels:
            app: influxdb
    serviceName: influxdb
    template:
        metadata:
            labels:
                app: influxdb
        spec:
            containers:      
              - image: influxdb:2.3.0-alpine
                name: influxdb
                ports:
                  - containerPort: 8086
                    name: influxdb
                volumeMounts:
                  - mountPath: /var/lib/influxdb2
                    name: data
    volumeClaimTemplates:
      - metadata:
            name: data
            namespace: influxdb
        spec:
            accessModes:
              - ReadWriteOnce
            resources:
                requests:
                    storage: 50G
---
apiVersion: v1
kind: Service
metadata:
  name: influxdb
  namespace: influxdb
spec:
  type: NodePort
  selector:
    app: influxdb
  ports:
    - protocol: TCP
      port: 8086
      targetPort: 8086
      nodePort: 30086

```

#### Visualization
grafana를 사용 하였습니다. 초기 암호는 admin / admin, 웹브라우저로 접근후 변경.


```
docker run -d --name=grafana \
  -p 3000:3000 \
  grafana/grafana
```

### stock-monitor bot
raspberry zero2w 에 설치하였습니다.   
hardware spec : 1GHz quad-core 64-bit ARM Cortex-A53 CPU and 512MB RAM.   




소스를 clone 받고...
config/.env.example 를 .env 로 복사하여 필요한 정보를 채워줍니다.
모니터링 하고자 하는 종목은  stocks.json에 저장되어 있습니다. 필요시 편집.
```
git clone https://github.com/Bozwell/stock-monitor
cd stock-monitor/app
cp config/.env.example config/.env
cp config/token.json.example config/token.json
```


docker build & run
```
docker build -t stock-monitor .
docker run -d -e TZ=Asia/Seoul -v $(pwd)/config:/app/config stock-monitor
```

### TODO
- 특정조건일때 telegram으로 알림하는 기능을 추가한다.

### References
- [한국투자증권 openapi](https://apiportal.koreainvestment.com/apiservice/oauth2#L_5c87ba63-740a-4166-93ac-803510bb9c02)
- [한국투저증권 github](https://github.com/koreainvestment/open-trading-api/tree/main/stocks_infotkanfkrekanfkr)

