# 宣城车e管 (e-FleetXuancheng)

本项目是一个基于 Vue.js 和 Flask 的车辆管理系统，旨在为宣城市某单位提供一个现代化、数据驱动的车队管理解决方案。系统通过直观的数据可视化界面，帮助管理人员全面掌握车队运营状况，优化资源分配，并提升管理效率。

## ✨ 主要功能

- **📊 整体概览**: 提供全局 KPI 指标，如车辆总数、部门总数，并通过图表展示月度里程、油耗、违章和维保的整体趋势。
- **🏢 部门总览与详情**:
    - **总览**: 对比各部门的里程、油耗、违章、维保数据，支持排名和分页查看。
    - **详情**: 提供单个部门的深入分析报告，包括部门 KPI、各项数据趋势、部门内车辆排名及车辆列表。
- **🚗 车辆总览与详情**:
    - **总览**: 展示所有车辆的关键运营数据，支持按不同指标排序和分页。
    - **详情**: 提供单辆车的全方位信息，包括基本资料、图片、月度里程、油耗、违章和维保的详细记录与趋势分析。
- **🔍 全局搜索**: 导航栏内置智能搜索框，支持快速查找指定的部门或车辆，并直接跳转至详情页。
- **⚙️ 数据管理**:
    - **增删改查**: 提供对车辆、违章、维保等核心数据的全功能后台管理。
    - **Excel 导入/导出**: 支持下载数据模板，并通过上传 Excel 文件批量导入数据，简化数据录入流程。

## 🛠️ 技术栈

- **前端**:
    - [Vue.js 3](https://vuejs.org/) (使用组合式 API)
    - [Vue Router](https://router.vuejs.org/)
    - [ECharts](https://echarts.apache.org/) & [vue-echarts](https://github.com/ecomfe/vue-echarts)
- **后端**:
    - [Flask](https://flask.palletsprojects.com/)
    - Python 3
    - SQLite
- **数据处理**:
    - [Pandas](https://pandas.pydata.org/) (用于处理 Excel 文件)

## 📁 项目结构

```
.
├── backend/         # 后端 Flask 应用
│   ├── app.py       # 主应用文件
│   └── data/        # 数据库文件目录
│       └── vehicle_data_optimized.db
├── be/              # 辅助脚本 (数据导入等)
├── doc/             # 项目文档
├── frontend/        # 前端 Vue.js 应用
│   ├── src/
│   │   ├── views/   # 页面组件
│   │   └── router/  # 路由配置
│   └── ...
└── README.md        # 项目说明
```

## 🚀 快速开始

### 1. 环境准备

- [Python](https://www.python.org/) (建议 3.8 或更高版本)
- [Node.js](https://nodejs.org/) (建议 16.x 或更高版本)

### 2. 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. (建议) 创建并激活虚拟环境
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS / Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动后端服务
python app.py
```
后端服务将运行在 `http://127.0.0.1:5000`。

### 3. 前端启动

```bash
# 1. 打开一个新的终端，进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```
前端开发服务器将运行在 `http://localhost:5173` (或其他可用端口)。在浏览器中打开此地址即可访问系统。

### 4. 数据库初始化

项目使用 SQLite 数据库，原始数据位于 `temp/` 目录下。您可以使用 `be/import_data.py` 脚本将原始的 CSV 数据导入到数据库中。
