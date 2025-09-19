import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

# --- 配置 ---
# 构建数据库文件的绝对路径
# __file__ 指向当前脚本 (app.py)
# os.path.dirname() 获取脚本所在的目录 (backend)
# os.path.join() 用于安全地拼接路径，'..' 代表上级目录
SCRIPT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'be', 'vehicle_data_optimized.db')


# --- Flask 应用初始化 ---
app = Flask(__name__)
# 启用 CORS (跨源资源共享)
# 这允许我们的前端页面 (可能在不同的源/端口上) 能够访问这个后端API
# 在生产环境中，应该将允许的源限制为你的前端域名，例如: CORS(app, origins="http://yourfrontend.com")
CORS(app)


# --- 数据库连接辅助函数 ---
def get_db_connection():
    """创建并返回一个到 SQLite 数据库的连接。"""
    conn = sqlite3.connect(DB_PATH)
    # 设置 row_factory，使得查询结果可以像字典一样通过列名访问，方便后续转换为 JSON
    conn.row_factory = sqlite3.Row
    return conn


# --- API 路由定义 ---

# 根路由，用于简单测试后端是否正在运行
@app.route('/')
def index():
    """一个简单的路由，用于确认后端正在运行。"""
    return "后端服务已成功启动!"

# 获取车辆列表的 API 接口
@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """
    API 端点，用于从数据库获取车辆列表。
    作为示例，这里只获取了前10条车辆数据。
    """
    try:
        # 1. 获取数据库连接
        conn = get_db_connection()
        # 2. 执行 SQL 查询
        vehicles = conn.execute('SELECT * FROM vehicles LIMIT 10').fetchall()
        # 3. 关闭数据库连接
        conn.close()
        # 4. 将查询结果 (Row 对象列表) 转换为字典列表，然后用 jsonify 转换为 JSON 格式的响应
        return jsonify([dict(row) for row in vehicles])
    except sqlite3.Error as e:
        # 如果发生数据库相关的错误，返回一个包含错误信息的 JSON 和 500 状态码
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        # 捕获其他可能的未知错误
        return jsonify({"error": f"发生意外错误: {e}"}), 500

# --- 新增 ---
# 为概览页提供汇总数据的 API 接口
@app.route('/api/overview/summary', methods=['GET'])
def get_overview_summary():
    """
    API 端点，用于获取概览页所需的汇总数据。
    (新增) 支持 start_month 和 end_month URL参数进行时间范围过滤。
    """
    try:
        # 从 URL 查询参数中获取月份，如果没有则为 None
        start_month = request.args.get('start_month') # 格式: YYYY-MM
        end_month = request.args.get('end_month')     # 格式: YYYY-MM

        conn = get_db_connection()
        
        # 1. 查询 KPI (这些通常是全时间范围的，不受筛选影响)
        total_vehicles = conn.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0]
        total_departments = conn.execute('SELECT COUNT(*) FROM departments').fetchone()[0]
        
        # (已移除) 不再查询各部门车辆数

        # --- 动态构建趋势查询的 WHERE 子句 ---
        
        params = {}
        violation_where = "WHERE violation_time IS NOT NULL"
        fuel_where = ""
        maint_where = "WHERE request_time IS NOT NULL"

        if start_month and end_month:
            params = {'start': f'{start_month}-01', 'end': f'{end_month}-31'}
            violation_where += " AND date(violation_time) BETWEEN date(:start) AND date(:end)"
            # 注意: fuel summary 表的月份是分开存储的，需要拼接
            fuel_where = "WHERE date(year || '-' || printf('%02d', month) || '-01') BETWEEN date(:start) AND date(:end)"
            maint_where += " AND date(request_time) BETWEEN date(:start) AND date(:end)"

        # 3. 查询月度违章趋势
        violation_trend = conn.execute(f"""
            SELECT strftime('%Y-%m', violation_time) as month, COUNT(violation_id) as count
            FROM violations
            {violation_where}
            GROUP BY month ORDER BY month
        """, params).fetchall()

        # 4. 查询月度油耗和里程趋势
        fuel_mileage_trend = conn.execute(f"""
            SELECT year || '-' || printf('%02d', month) as month, 
                   SUM(total_fuel_amount) as total_fuel,
                   SUM(distance_driven) as total_distance
            FROM monthly_fuel_summary
            {fuel_where}
            GROUP BY month ORDER BY month
        """, params).fetchall()

        # 5. 查询月度维保费用趋势
        maintenance_trend = conn.execute(f"""
            SELECT strftime('%Y-%m', request_time) as month, SUM(maintenance_cost) as total_cost
            FROM maintenance
            {maint_where}
            GROUP BY month ORDER BY month
        """, params).fetchall()
        
        conn.close()

        # (修改) 准备图表数据时，移除 vehicles_per_department
        chart_data = {
            'violation_trend': {
                'labels': [row['month'] for row in violation_trend],
                'data': [row['count'] for row in violation_trend]
            },
            'fuel_trend': {
                'labels': [row['month'] for row in fuel_mileage_trend],
                'data': [row['total_fuel'] for row in fuel_mileage_trend]
            },
            'mileage_trend': {
                'labels': [row['month'] for row in fuel_mileage_trend],
                'data': [row['total_distance'] for row in fuel_mileage_trend]
            },
            'maintenance_trend': {
                'labels': [row['month'] for row in maintenance_trend],
                'data': [row['total_cost'] for row in maintenance_trend]
            }
        }

        # 组装最终的 JSON 响应
        summary_data = {
            'kpi': {
                'total_vehicles': total_vehicles,
                'total_departments': total_departments
            },
            'charts': chart_data
        }
        
        return jsonify(summary_data)
        
    except sqlite3.Error as e:
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"发生意外错误: {e}"}), 500


# --- 主程序入口 ---
if __name__ == '__main__':
    # 启动 Flask 开发服务器
    # debug=True: 开启调试模式，当代码有改动时服务器会自动重启，并提供详细的错误页面
    # port=5000: 指定服务器运行的端口
    # 在生产环境中，应使用更专业的 WSGI 服务器，如 Gunicorn 或 Waitress
    app.run(debug=True, port=5000)
