# LoomLot-01 · 染坊缸染与色牢度抽检

靛蓝染坊台：按 **染坊 → 染缸 → 染程 → 色牢度** 工序推进，聚焦缸染调度与抽检，不是库存出入库系统。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Backend | FastAPI + SQLAlchemy 2 + Pydantic v2 + Postgres + JWT |
| Frontend | Svelte 4 + Vite + svelte-spa-router |
| 部署 | docker-compose（db + backend + frontend/nginx） |

## 端口

| 服务 | 端口 |
| --- | --- |
| 前端 | **3600** |
| 后端 API | **8600** |
| PostgreSQL | **5439** |

数据库账号：`loomlot` / `loomlot` / 库名 `loomlot`。

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 染坊主管 |
| `dyer` | `123456` | 染程操作员 |

容器启动时 entrypoint 自动建表并 seed。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\LoomLot\LoomLot-01
docker compose up -d --build
```

浏览器：http://localhost:3600  
API：http://localhost:8600/api/health

停止：

```bash
docker compose down
```

## 业务实体

1. **DyeHouse** — `name`, `waterHardnessMgL`(0–500, 必填), `waterReused`(bool, 必填), `waterNote`(可选水源备注), `notes`
2. **Vat** — `dyeHouseId`, `vatCode`, `fiberType`, `capacityL`, `status` ∈ `ready|dyeing|drain`
3. **DyeLot** — `vatId`, `recipeName`, `fabricKg`, `startedAt`, `operatorName`
4. **FastnessCheck** — `dyeLotId`, `checkedAt`, `washFastness`(1–5), `rubFastness`(>0), `tempC`, `notes`

### 规则

- 仅当染缸状态为 `ready` 或 `dyeing` 时可新建染程，否则 409
- 新建染程后，染缸状态自动设为 `dyeing`
- 染坊水源硬度 `waterHardnessMgL` 取值 0–500，`waterReused` 必填；新建两字段必填，更新时两字段必须一并补齐（缺字段 400）。原自由文本 `waterNote` 改为可选备注
- 染坊水源硬度 **> 200 mg/L** 时，该坊染缸上新建/更新染程布重 `fabricKg` 不得超过 **30 kg**，超限返回 **400**，错误信息点明因硬度；染程改挂染缸时按目标缸所属染坊判定
- 染坊 `waterReused=true` 时，该坊禁止新建或修改染缸纤维为含「棉」字样，违者 **409**；染缸改挂染坊时按目标染坊判定
- 上述硬度/回用水规则在染程路由与染缸路由共用 `app/services/water_rules.py` 同一套判定
- 染坊列表支持 `GET /api/dye-houses?reusedOnly=true` 仅筛回用水坊；看板 `reusedWaterHouseCount` 与该筛选行数一致
- 染程列表支持 `GET /api/dye-lots?hardnessLimitedActive=true` 筛「硬度>200 且进行中（染缸 dyeing）」染程；看板 `hardnessLimitedActiveLotCount` 与该筛选手数一致（共用同一查询条件）
- 可选接口：`POST /api/vats/{id}/drain` 将染缸置为 `drain`

## 主要 API

- `POST /api/auth/login`（OAuth2 表单）
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/dye-houses`
- `GET/POST/PUT/DELETE /api/vats` · `POST /api/vats/{id}/drain`
- `GET/POST/PUT/DELETE /api/dye-lots`
- `GET/POST/PUT/DELETE /api/fastness-checks`
- `GET /api/dashboard/stats`

除登录外需 `Authorization: Bearer <token>`。字段对外为 camelCase。

## 目录

```
LoomLot-01/
├── docker-compose.yml
├── backend/          # FastAPI
├── frontend/         # Svelte 4 + Vite + nginx
└── README.md
```

## 本地开发

### 数据库

```bash
docker compose up -d db
```

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://loomlot:loomlot@127.0.0.1:5439/loomlot"
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8600
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发态 Vite 将 `/api` 代理到 `http://127.0.0.1:8600`。
