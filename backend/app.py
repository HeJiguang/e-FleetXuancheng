import sqlite3
from flask import Flask, jsonify, request, send_file, url_for, send_from_directory
from flask_cors import CORS
import os
import pandas as pd
import io
from werkzeug.utils import secure_filename
import uuid

# --- 配置 ---
# 构建数据库文件的绝对路径
# __file__ 指向当前脚本 (app.py)
# os.path.dirname() 获取脚本所在的目录 (backend)
# os.path.join() 用于安全地拼接路径，'..' 代表上级目录
# 定义数据库文件路径
# (修改) 更新数据库文件的相对路径，指向 backend/data/ 目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'data', 'vehicle_data_optimized.db')
# (新增) 上传文件夹配置
UPLOAD_FOLDER = os.path.join(SCRIPT_DIR, 'uploads', 'vehicle_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# (新增) 中英文列名映射
COLUMN_MAPPING = {
    'vehicles': {
        'plate_number': '车牌号',
        'department_id': '部门ID',
        'manager': '车管员',
        'brand_model': '品牌型号',
        'displacement': '排量',
        'capacity': '载重',
        'registration_date': '注册日期',
        'purchase_price': '采购价格',
        'notes': '备注'
    },
    'violations': {
        'plate_number': '车牌号',
        'violation_time': '违章时间',
        'violation_location': '违章地点',
        'violation_type_id': '违章类型ID'
    },
    'maintenance': {
        'plate_number': '车牌号',
        'order_number': '工单号',
        'provider_id': '维保服务商ID',
        'request_time': '申请时间',
        'delivery_time': '交付时间',
        'current_mileage': '当前里程',
        'last_maintenance_mileage': '上次维保里程',
        'service_details': '维保详情',
        'maintenance_cost': '维保费用'
    },
    'monthly_fuel_summary': {
        'plate_number': '车牌号',
        'year': '年份',
        'month': '月份',
        'total_fuel_cost': '油耗总花费',
        'total_fuel_amount': '油耗总量(升)',
        'start_month_mileage': '月初里程',
        'end_month_mileage': '月末里程',
        'distance_driven': '行驶里程(公里)',
        'avg_consumption_per_100km': '百公里平均油耗(升)',
        'card_number': '加油卡号',
        'notes': '备注'
    }
}


# --- Flask 应用初始化 ---
app = Flask(__name__)
# 启用 CORS (跨源资源共享)
# 这允许我们的前端页面 (可能在不同的源/端口上) 能够访问这个后端API
# 在生产环境中，应该将允许的源限制为你的前端域名，例如: CORS(app, origins="http://yourfrontend.com")
CORS(app)
# (新增) 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- 数据库连接辅助函数 ---
def get_db_connection():
    """创建并返回一个到 SQLite 数据库的连接。"""
    conn = sqlite3.connect(DB_FILE)
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
        
        # (新增) 查询各部门车辆数分布
        vehicles_per_department = conn.execute("""
            SELECT d.department_id, d.name, COUNT(v.vehicle_id) as count
            FROM departments d
            LEFT JOIN vehicles v ON d.department_id = v.department_id
            GROUP BY d.department_id, d.name
            ORDER BY count DESC
        """).fetchall()

        # (已移除) 不再查询各部门车辆数

        # --- 动态构建趋势查询的 WHERE 子句 ---
        
        # (修改) 重构WHERE子句的构建逻辑，使其更清晰和健壮
        time_filter_params = {}
        # 为带别名和不带别名的查询分别准备 WHERE 子句
        violation_where_aliased = "WHERE v.violation_time IS NOT NULL"
        violation_where_no_alias = "WHERE violation_time IS NOT NULL"
        maint_where_aliased = "WHERE m.request_time IS NOT NULL"
        maint_where_no_alias = "WHERE request_time IS NOT NULL"
        fuel_where = ""

        if start_month and end_month:
            time_filter_params = {'start': f'{start_month}-01', 'end': f'{end_month}-31'}
            
            # 为每个子句附加时间范围条件
            violation_where_aliased += " AND date(v.violation_time) BETWEEN date(:start) AND date(:end)"
            violation_where_no_alias += " AND date(violation_time) BETWEEN date(:start) AND date(:end)"
            maint_where_aliased += " AND date(m.request_time) BETWEEN date(:start) AND date(:end)"
            maint_where_no_alias += " AND date(request_time) BETWEEN date(:start) AND date(:end)"
            fuel_where = "WHERE date(year || '-' || printf('%02d', month) || '-01') BETWEEN date(:start) AND date(:end)"


        # 3. 查询月度违章趋势
        violation_trend = conn.execute(f"""
            SELECT strftime('%Y-%m', violation_time) as month, COUNT(violation_id) as count
            FROM violations
            {violation_where_no_alias}
            GROUP BY month ORDER BY month
        """, time_filter_params).fetchall()

        # 4. 查询月度油耗和里程趋势
        fuel_mileage_trend = conn.execute(f"""
            SELECT year || '-' || printf('%02d', month) as month, 
                   SUM(total_fuel_amount) as total_fuel,
                   SUM(distance_driven) as total_distance,
                   SUM(total_fuel_cost) as total_fuel_cost
            FROM monthly_fuel_summary s
            {fuel_where}
            GROUP BY month ORDER BY month
        """, time_filter_params).fetchall()

        # 5. 查询月度维保费用趋势
        maintenance_trend = conn.execute(f"""
            SELECT strftime('%Y-%m', request_time) as month, 
                   SUM(maintenance_cost) as total_cost,
                   COUNT(maintenance_id) as total_count
            FROM maintenance
            {maint_where_no_alias}
            GROUP BY month ORDER BY month
        """, time_filter_params).fetchall()
        
        # (新增) --- 查询深度洞察 KPI ---
        insight_kpis = {}
        
        # 最高频违章路段
        top_location = conn.execute(f"""
            SELECT v.violation_location, COUNT(v.violation_id) as count
            FROM violations v
            {violation_where_aliased} AND v.violation_location IS NOT NULL AND v.violation_location != ''
            GROUP BY v.violation_location
            ORDER BY count DESC LIMIT 1
        """, time_filter_params).fetchone()
        insight_kpis['top_violation_location'] = dict(top_location) if top_location else None

        # 最高频违章原因
        top_reason = conn.execute(f"""
            SELECT t.description, COUNT(v.violation_id) as count
            FROM violations v
            JOIN violation_types t ON v.violation_type_id = t.violation_type_id
            {violation_where_aliased}
            GROUP BY t.description
            ORDER BY count DESC LIMIT 1
        """, time_filter_params).fetchone()
        insight_kpis['top_violation_reason'] = dict(top_reason) if top_reason else None

        # 最常用维保单位
        top_provider = conn.execute(f"""
            SELECT p.name, COUNT(m.maintenance_id) as count
            FROM maintenance m
            JOIN service_providers p ON m.provider_id = p.provider_id
            {maint_where_aliased}
            GROUP BY p.name
            ORDER BY count DESC LIMIT 1
        """, time_filter_params).fetchone()
        insight_kpis['top_maintenance_provider'] = dict(top_provider) if top_provider else None

        
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
            },
            # (新增) 维保次数趋势
            'maintenance_count_trend': {
                'labels': [row['month'] for row in maintenance_trend],
                'data': [row['total_count'] for row in maintenance_trend]
            },
            # (新增) 部门车辆分布图数据
            'vehicles_per_department': {
                'labels': [row['name'] for row in vehicles_per_department],
                'data': [row['count'] for row in vehicles_per_department],
                'department_ids': [row['department_id'] for row in vehicles_per_department]
            }
        }

        # (修改) 组装最终的 JSON 响应
        summary_data = {
            'kpi': {
                'total_vehicles': total_vehicles,
                'total_departments': total_departments,
                # (新增) 增加汇总数据
                'total_distance': sum(r['total_distance'] for r in fuel_mileage_trend),
                'total_fuel': sum(r['total_fuel'] for r in fuel_mileage_trend),
                'total_fuel_cost': sum(r['total_fuel_cost'] for r in fuel_mileage_trend),
                'total_violations': sum(r['count'] for r in violation_trend),
                'total_maintenance_cost': sum(r['total_cost'] for r in maintenance_trend),
                'total_maintenance_count': sum(r['total_count'] for r in maintenance_trend)
            },
            'charts': chart_data,
            'insight_kpis': insight_kpis # (新增)
        }
        
        return jsonify(summary_data)
        
    except sqlite3.Error as e:
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"发生意外错误: {e}"}), 500

# (新增) ===============================================
#       部门总览页面的 API 端点
# =====================================================
@app.route('/api/department/summary', methods=['GET'])
def get_department_summary():
    """
    API 端点，用于获取部门总览页所需的数据。
    - 按部门汇总各项指标（里程、油耗、违章、维保）
    - 支持时间范围筛选
    - (修改) 不再支持分页，返回所有部门
    """
    try:
        # (移除) 移除分页参数
        # page = request.args.get('page', default=1, type=int)
        # per_page = request.args.get('per_page', default=10, type=int)
        # offset = (page - 1) * per_page
        
        start_month = request.args.get('start_month')
        end_month = request.args.get('end_month')
        
        conn = get_db_connection()

        # (移除) 移除部门总数查询
        # total_departments_count = conn.execute('SELECT COUNT(*) FROM departments').fetchone()[0]

        # (修改) 移除分页 LIMIT 和 OFFSET
        depts_query = """
            SELECT d.department_id, d.name, COUNT(v.vehicle_id) as vehicle_count
            FROM departments d
            LEFT JOIN vehicles v ON d.department_id = v.department_id
            GROUP BY d.department_id, d.name
            ORDER BY d.department_id
        """
        departments = {row['department_id']: dict(row) for row in conn.execute(depts_query).fetchall()}
        
        # 如果没有部门，直接返回空结果
        if not departments:
            conn.close()
            return jsonify({
                'departments': [],
                'kpis': {}
                # (移除) 移除分页信息
            })


        # 初始化聚合数据
        for dept_id in departments:
            departments[dept_id].update({
                'total_distance': 0, 'total_fuel': 0, 'violation_count': 0, 'total_maintenance_cost': 0
            })

        # --- 动态构建 WHERE 子句 ---
        params = {}
        where_clauses = {}
        if start_month and end_month:
            params = {'start': f'{start_month}-01', 'end': f'{end_month}-31'}
            where_clauses['fuel'] = "WHERE date(s.year || '-' || printf('%02d', s.month) || '-01') BETWEEN date(:start) AND date(:end)"
            where_clauses['violation'] = "WHERE date(i.violation_time) BETWEEN date(:start) AND date(:end)"
            where_clauses['maint'] = "WHERE date(m.request_time) BETWEEN date(:start) AND date(:end)"

        # 1. 聚合各部门的里程和油耗
        fuel_mileage_query = f"""
            SELECT v.department_id, SUM(s.distance_driven) as total_distance, SUM(s.total_fuel_amount) as total_fuel
            FROM monthly_fuel_summary s
            JOIN vehicles v ON s.plate_number = v.plate_number
            {where_clauses.get('fuel', '')}
            AND v.department_id IN ({','.join('?' for _ in departments.keys())})
            GROUP BY v.department_id
        """
        for row in conn.execute(fuel_mileage_query, list(params.values()) + list(departments.keys())).fetchall():
            if row['department_id'] in departments:
                departments[row['department_id']].update(dict(row))

        # 2. 聚合各部门的违章数
        violations_query = f"""
            SELECT v.department_id, COUNT(i.violation_id) as violation_count
            FROM violations i
            JOIN vehicles v ON i.plate_number = v.plate_number
            {where_clauses.get('violation', '')}
            AND v.department_id IN ({','.join('?' for _ in departments.keys())})
            GROUP BY v.department_id
        """
        for row in conn.execute(violations_query, list(params.values()) + list(departments.keys())).fetchall():
            if row['department_id'] in departments:
                departments[row['department_id']].update(dict(row))

        # 3. 聚合各部门的维保费用
        maint_query = f"""
            SELECT v.department_id, SUM(m.maintenance_cost) as total_maintenance_cost
            FROM maintenance m
            JOIN vehicles v ON m.plate_number = v.plate_number
            {where_clauses.get('maint', '')}
            AND v.department_id IN ({','.join('?' for _ in departments.keys())})
            GROUP BY v.department_id
        """
        # (修改) 更新参数传递方式以匹配 IN 子句
        maint_params = list(params.values()) + list(departments.keys())
        for row in conn.execute(maint_query, maint_params).fetchall():
            if row['department_id'] in departments:
                departments[row['department_id']].update(dict(row))
        
        # (新增) 为了计算全局KPI，需要查询所有部门的数据，不受分页影响
        # 1. 查询所有部门的车辆总数
        total_vehicles_count = conn.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0]
        # 2. 查询所有部门在时间范围内的总里程、油耗、违章、维保
        all_depts_fuel_mileage = conn.execute(f"""
            SELECT SUM(s.distance_driven) as total_distance, SUM(s.total_fuel_amount) as total_fuel
            FROM monthly_fuel_summary s {where_clauses.get('fuel', '').replace('s.year', 'year').replace('s.month','month')}
        """, params).fetchone()
        
        all_depts_violations = conn.execute(f"""
            SELECT COUNT(i.violation_id) as violation_count
            FROM violations i {where_clauses.get('violation', '').replace('i.violation_time','violation_time')}
        """, params).fetchone()

        all_depts_maint = conn.execute(f"""
            SELECT SUM(m.maintenance_cost) as total_maintenance_cost
            FROM maintenance m {where_clauses.get('maint', '').replace('m.request_time','request_time')}
        """, params).fetchone()

        conn.close()

        # (修改) 基于对所有部门的查询来计算全局 KPI
        kpis = {
            'total_vehicles': total_vehicles_count,
            'total_departments': len(departments), # (修改) 直接使用查询到的部门数量
            'total_distance': all_depts_fuel_mileage['total_distance'] or 0,
            'total_fuel': all_depts_fuel_mileage['total_fuel'] or 0,
            'violation_count': all_depts_violations['violation_count'] or 0,
            'total_maintenance_cost': all_depts_maint['total_maintenance_cost'] or 0,
        }

        # 将字典转换为列表，方便前端 v-for 渲染
        department_list = list(departments.values())

        # (移除) 移除分页元数据
        
        # (修改) 包装响应数据，移除分页信息
        return jsonify({
            'departments': department_list,
            'kpis': kpis
        })

    except sqlite3.Error as e:
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"发生意外错误: {e}"}), 500


@app.route('/api/vehicle/summary', methods=['GET'])
def get_vehicle_summary():
    """
    API 端点，用于获取车辆总览页所需的数据。
    - 按车辆汇总各项指标（里程、油耗、违章、维保）
    - 支持分页和时间范围筛选
    """
    try:
        # 获取查询参数
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)
        sort_by = request.args.get('sort_by', default='mileage', type=str)
        sort_order = request.args.get('sort_order', default='desc', type=str)
        start_month = request.args.get('start_month')
        end_month = request.args.get('end_month')
        
        # 验证排序字段
        valid_sort_fields = {'mileage': 'total_distance', 'fuel': 'total_fuel', 
                            'violations': 'violation_count', 'maintenance': 'total_maintenance_cost'}
        
        if sort_by not in valid_sort_fields:
            sort_by = 'mileage'  # 默认按里程排序
            
        sort_field = valid_sort_fields[sort_by]
        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        conn = get_db_connection()
        
        # 构建时间筛选条件
        params = {}
        where_clauses = {}
        if start_month and end_month:
            params = {'start': f'{start_month}-01', 'end': f'{end_month}-31'}
            where_clauses['fuel'] = "WHERE date(s.year || '-' || printf('%02d', s.month) || '-01') BETWEEN date(:start) AND date(:end)"
            where_clauses['violation'] = "WHERE date(i.violation_time) BETWEEN date(:start) AND date(:end)"
            where_clauses['maint'] = "WHERE date(m.request_time) BETWEEN date(:start) AND date(:end)"
        
        # 1. 获取车辆基本信息和部门名称
        base_query = """
            SELECT v.vehicle_id, v.plate_number, v.registration_date as purchase_date, 
                   d.name as department_name
            FROM vehicles v
            LEFT JOIN departments d ON v.department_id = d.department_id
        """
        
        # 2. 构建车辆总数查询
        count_query = """
            SELECT COUNT(*) as total_vehicles FROM vehicles
        """
        total_vehicles = conn.execute(count_query).fetchone()['total_vehicles']
        
        # 3. 获取里程和油耗数据
        mileage_fuel_query = f"""
            SELECT v.plate_number,
                   SUM(s.distance_driven) as total_distance,
                   SUM(s.total_fuel_amount) as total_fuel
            FROM vehicles v
            LEFT JOIN monthly_fuel_summary s ON v.plate_number = s.plate_number
            {where_clauses.get('fuel', '')}
            GROUP BY v.plate_number
        """
        
        # 4. 获取违章数据
        violations_query = f"""
            SELECT v.plate_number,
                   COUNT(i.violation_id) as violation_count
            FROM vehicles v
            LEFT JOIN violations i ON v.plate_number = i.plate_number
            {where_clauses.get('violation', '')}
            GROUP BY v.plate_number
        """
        
        # 5. 获取维保数据
        maintenance_query = f"""
            SELECT v.plate_number,
                   SUM(m.maintenance_cost) as total_maintenance_cost
            FROM vehicles v
            LEFT JOIN maintenance m ON v.plate_number = m.plate_number
            {where_clauses.get('maint', '')}
            GROUP BY v.plate_number
        """
        
        # 6. 构建完整汇总查询
        full_query = f"""
            SELECT b.*, 
                   COALESCE(mf.total_distance, 0) as total_distance,
                   COALESCE(mf.total_fuel, 0) as total_fuel,
                   COALESCE(v.violation_count, 0) as violation_count,
                   COALESCE(m.total_maintenance_cost, 0) as total_maintenance_cost
            FROM ({base_query}) b
            LEFT JOIN ({mileage_fuel_query}) mf ON b.plate_number = mf.plate_number
            LEFT JOIN ({violations_query}) v ON b.plate_number = v.plate_number
            LEFT JOIN ({maintenance_query}) m ON b.plate_number = m.plate_number
            ORDER BY {sort_field} {sort_direction}
            LIMIT :limit OFFSET :offset
        """
        
        # 执行分页查询
        offset = (page - 1) * per_page
        params.update({'limit': per_page, 'offset': offset})
        vehicles_paged = conn.execute(full_query, params).fetchall()
        
        # (修改) 获取所有车辆的汇总数据，用于图表排名计算
        all_vehicles_summary_query = f"""
            SELECT b.*, 
                   COALESCE(mf.total_distance, 0) as total_distance,
                   COALESCE(mf.total_fuel, 0) as total_fuel,
                   COALESCE(v.violation_count, 0) as violation_count,
                   COALESCE(m.total_maintenance_cost, 0) as total_maintenance_cost
            FROM ({base_query}) b
            LEFT JOIN ({mileage_fuel_query}) mf ON b.plate_number = mf.plate_number
            LEFT JOIN ({violations_query}) v ON b.plate_number = v.plate_number
            LEFT JOIN ({maintenance_query}) m ON b.plate_number = m.plate_number
        """
        all_vehicles_summary = conn.execute(all_vehicles_summary_query, {k: v for k, v in params.items() if k not in ['limit', 'offset']}).fetchall()

        # (新增) 基于所有车辆的汇总数据计算 KPI
        kpis = {
            'total_distance': 0,
            'total_fuel': 0,
            'violation_count': 0,
            'total_maintenance_cost': 0,
        }
        if all_vehicles_summary:
            kpis['total_distance'] = sum(row['total_distance'] for row in all_vehicles_summary)
            kpis['total_fuel'] = sum(row['total_fuel'] for row in all_vehicles_summary)
            kpis['violation_count'] = sum(row['violation_count'] for row in all_vehicles_summary)
            kpis['total_maintenance_cost'] = sum(row['total_maintenance_cost'] for row in all_vehicles_summary)


        # 7. 获取排名前10的车辆数据（用于图表）
        chart_data = {}
        for metric in ['mileage', 'fuel', 'violations', 'maintenance']:
            field_name = valid_sort_fields[metric] # 获取实际的数据库字段名
            
            # 在 Python 中对所有车辆汇总数据进行排序和筛选
            sorted_data = sorted(all_vehicles_summary, key=lambda x: x[field_name], reverse=True)
            # (修改) 不再截取 top_10，而是使用所有已排序的数据
            
            # 为图表准备数据
            chart_data[metric] = {
                'labels': [row['plate_number'] for row in sorted_data],
                'data': [row[field_name] for row in sorted_data],
                'departments': [row['department_name'] for row in sorted_data]
            }
        
        conn.close()
        
        # 构造分页元数据
        pagination = {
            'total': total_vehicles,
            'per_page': per_page,
            'current_page': page,
            'total_pages': (total_vehicles + per_page - 1) // per_page
        }
        
        return jsonify({
            'vehicles': [dict(row) for row in vehicles_paged],
            'pagination': pagination,
            'chart_data': chart_data,
            'kpis': kpis # (新增) 在响应中加入 KPI 数据
        })

    except sqlite3.Error as e:
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"发生意外错误: {e}"}), 500


# (新增) ===============================================
#       数据管理页面的 API 端点
# =====================================================

def get_table_data(table_name, columns):
    """通用函数，用于获取指定表的数据，支持分页和排序"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort_by', columns[0], type=str)
    sort_order = request.args.get('sort_order', 'asc', type=str)
    
    if sort_by not in columns:
        sort_by = columns[0]
    
    sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
    
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    
    # 构建查询
    query = f"SELECT * FROM {table_name} ORDER BY {sort_by} {sort_direction} LIMIT ? OFFSET ?"
    data = conn.execute(query, (per_page, offset)).fetchall()
    
    # 获取总数
    total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'data': [dict(row) for row in data],
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    })

@app.route('/api/data/<table>', methods=['GET'])
def get_data(table):
    """动态获取不同表的数据"""
    table_columns = {
        'vehicles': ['vehicle_id', 'plate_number', 'department_id', 'manager', 'brand_model', 'registration_date'],
        'violations': ['violation_id', 'plate_number', 'violation_time', 'violation_location'],
        'maintenance': ['maintenance_id', 'plate_number', 'request_time', 'maintenance_cost'],
        'monthly_fuel_summary': ['summary_id', 'plate_number', 'year', 'month', 'total_fuel_cost']
    }
    if table in table_columns:
        return get_table_data(table, table_columns[table])
    return jsonify({"error": "Invalid table"}), 404

@app.route('/api/data/<table>', methods=['POST'])
def add_record(table):
    """动态添加记录到指定表"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    conn = get_db_connection()
    try:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        conn.execute(query, tuple(data.values()))
        conn.commit()
        # 获取新插入记录的ID (假设主键是自增的)
        new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        return jsonify({"message": "Record added successfully", "id": new_id}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/data/<table>/<id>', methods=['PUT'])
def update_record(table, id):
    """动态更新指定表中的记录"""
    id_column_map = {
        'vehicles': 'vehicle_id',
        'violations': 'violation_id',
        'maintenance': 'maintenance_id',
        'monthly_fuel_summary': 'summary_id'
    }
    if table not in id_column_map:
        return jsonify({"error": "Invalid table"}), 404
    
    id_column = id_column_map[table]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    conn = get_db_connection()
    try:
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?"
        
        values = list(data.values())
        values.append(id)
        
        conn.execute(query, tuple(values))
        conn.commit()
        return jsonify({"message": "Record updated successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/data/<table>/<id>', methods=['DELETE'])
def delete_record(table, id):
    """动态删除指定表中的记录"""
    id_column_map = {
        'vehicles': 'vehicle_id',
        'violations': 'violation_id',
        'maintenance': 'maintenance_id',
        'monthly_fuel_summary': 'summary_id'
    }
    if table not in id_column_map:
        return jsonify({"error": "Invalid table"}), 404
        
    id_column = id_column_map[table]
    
    try:
        conn = get_db_connection()
        conn.execute(f"DELETE FROM {table} WHERE {id_column} = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Record deleted successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download-template/<table>', methods=['GET'])
def download_template(table):
    """为指定表生成并提供Excel模板文件下载（中文表头）"""
    if table not in COLUMN_MAPPING:
        return jsonify({"error": "Invalid table for template generation"}), 404

    # 获取中文表头
    chinese_headers = list(COLUMN_MAPPING[table].values())
    
    df = pd.DataFrame(columns=chinese_headers)
    
    # 使用BytesIO作为内存中的文件
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close() # 在 2.0 版本中，pd.ExcelWriter.close() 是保存文件的正确方法
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{table}_template.xlsx'
    )

@app.route('/api/upload/<table>', methods=['POST'])
def upload_file(table):
    """处理文件上传并将数据导入数据库（支持中文表头）"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            if table not in COLUMN_MAPPING:
                return jsonify({"error": "Invalid table for data import"}), 404

            df = pd.read_excel(file, engine='openpyxl')
            
            # (新增) 数据清洗和预处理
            df.dropna(how='all', inplace=True)
            df.columns = df.columns.str.strip()

            # (新增) 将中文表头映射回英文数据库列名
            reverse_mapping = {v: k for k, v in COLUMN_MAPPING[table].items()}
            df.rename(columns=reverse_mapping, inplace=True)
            
            # 检查是否有未匹配的列
            expected_columns = COLUMN_MAPPING[table].keys()
            unmatched_columns = [col for col in df.columns if col not in expected_columns]
            if unmatched_columns:
                 return jsonify({"error": f"上传的文件中包含无法识别的列: {', '.join(unmatched_columns)}"}), 400

            conn = get_db_connection()
            # to_sql 会自动处理列映射和数据插入
            # if_exists='append' 表示如果表已存在，则追加数据
            # index=False 表示不将DataFrame的索引写入数据库
            df.to_sql(table, conn, if_exists='append', index=False)
            conn.close()
            
            return jsonify({"message": f"成功上传并导入数据到 '{table}' 表."}), 200
        except Exception as e:
            return jsonify({"error": f"发生错误: {str(e)}"}), 500
            
    return jsonify({"error": "无效的文件类型"}), 400


# (移除) 不再需要的趋势图API端点
# @app.route('/api/department/trends', methods=['GET'])
# def get_department_trends():
#     """
#     API 端点，用于获取各部门的时间趋势数据，目前仅为里程。
#     """
#     try:
#         start_month = request.args.get('start_month')
#         end_month = request.args.get('end_month')
        
#         conn = get_db_connection()

#         params = {}
#         where_clause = ""
#         if start_month and end_month:
#             params = {'start': f'{start_month}-01', 'end': f'{end_month}-31'}
#             where_clause = "WHERE date(s.year || '-' || printf('%02d', s.month) || '-01') BETWEEN date(:start) AND date(:end)"

#         query = f"""
#             SELECT
#                 d.name as department_name,
#                 s.year || '-' || printf('%02d', s.month) as month,
#                 SUM(s.distance_driven) as total_distance
#             FROM monthly_fuel_summary s
#             JOIN vehicles v ON s.plate_number = v.plate_number
#             JOIN departments d ON v.department_id = d.department_id
#             {where_clause}
#             GROUP BY d.name, month
#             ORDER BY month, d.name;
#         """
        
#         rows = conn.execute(query, params).fetchall()
#         conn.close()

#         # --- 数据透视转换 ---
#         # 目标: 将扁平的SQL结果转换为Chart.js需要的数据结构
        
#         # 1. 获取所有月份标签和部门
#         labels = sorted(list(set(row['month'] for row in rows)))
#         departments = sorted(list(set(row['department_name'] for row in rows)))
        
#         # 2. 创建一个数据字典，方便快速查找
#         data_map = {}
#         for row in rows:
#             data_map[(row['department_name'], row['month'])] = row['total_distance']
            
#         # 3. 构建 Chart.js 的 datasets
#         datasets = []
#         for dept in departments:
#             dataset = {
#                 'label': dept,
#                 'data': [data_map.get((dept, month), 0) for month in labels],
#                 'fill': False,
#                 'tension': 0.1
#             }
#             datasets.append(dataset)
            
#         return jsonify({'labels': labels, 'datasets': datasets})

#     except sqlite3.Error as e:
#         return jsonify({"error": f"数据库错误: {e}"}), 500
#     except Exception as e:
#         return jsonify({"error": f"发生意外错误: {e}"}), 500


# (新增) ===============================================
#       车辆详情页面的 API 端点
# =====================================================
@app.route('/api/vehicle/detail/<plate_number>', methods=['GET'])
def get_vehicle_detail(plate_number):
    """
    API 端点，获取单个车辆的详细信息，用于车辆详情页。
    (新增) 支持 start_month 和 end_month URL参数进行时间范围过滤。
    """
    try:
        # (新增) 从 URL 查询参数中获取月份
        start_month = request.args.get('start_month') # 格式: YYYY-MM
        end_month = request.args.get('end_month')     # 格式: YYYY-MM

        conn = get_db_connection()
        
        # 1. 查询车辆基本信息 (不受时间筛选影响)
        basic_info_query = """
            SELECT v.*, d.name as department_name
            FROM vehicles v
            LEFT JOIN departments d ON v.department_id = d.department_id
            WHERE v.plate_number = ?
        """
        basic_info = conn.execute(basic_info_query, (plate_number,)).fetchone()

        if not basic_info:
            return jsonify({"error": "Vehicle not found"}), 404
        
        basic_info_dict = dict(basic_info)
        # (修改) 根据数据库中的 image_url 构建完整的图片访问 URL
        if basic_info_dict.get('image_url'):
            # url_for('uploaded_file', filename=...) 会生成 /uploads/vehicle_images/xxx.png 这样的URL
            basic_info_dict['vehicle_image_url'] = url_for('uploaded_file', filename=basic_info_dict['image_url'], _external=True)
        else:
            basic_info_dict['vehicle_image_url'] = f'https://via.placeholder.com/800x500.png?text={plate_number}'

        department_id = basic_info_dict['department_id']
        
        # (新增) --- 动态构建 WHERE 子句 ---
        params = {'plate_number': plate_number}
        time_filter_clauses = {
            'fuel_mileage': '',
            'violations': '',
            'maintenance': ''
        }
        if start_month and end_month:
            params.update({'start': f'{start_month}-01', 'end': f'{end_month}-31'})
            time_filter_clauses['fuel_mileage'] = "AND date(year || '-' || printf('%02d', month) || '-01') BETWEEN date(:start) AND date(:end)"
            time_filter_clauses['violations'] = "AND date(v.violation_time) BETWEEN date(:start) AND date(:end)"
            time_filter_clauses['maintenance'] = "AND date(m.request_time) BETWEEN date(:start) AND date(:end)"


        # 2. 查询里程和油耗信息 (月度汇总表)
        fuel_mileage_details = conn.execute(f"""
            SELECT year || '-' || printf('%02d', month) as month, distance_driven, total_fuel_amount, total_fuel_cost, avg_consumption_per_100km
            FROM monthly_fuel_summary
            WHERE plate_number = :plate_number {time_filter_clauses['fuel_mileage']}
            ORDER BY month
        """, params).fetchall()
        
        # 3. 查询违章详情
        violation_details = conn.execute(f"""
            SELECT v.violation_time, v.violation_location, t.description as violation_reason
            FROM violations v
            LEFT JOIN violation_types t ON v.violation_type_id = t.violation_type_id
            WHERE v.plate_number = :plate_number {time_filter_clauses['violations']}
            ORDER BY v.violation_time DESC
        """, params).fetchall()
        
        # 4. 查询维保详情
        maintenance_details = conn.execute(f"""
            SELECT m.request_time, m.service_details, m.maintenance_cost, p.name as provider_name
            FROM maintenance m
            LEFT JOIN service_providers p ON m.provider_id = p.provider_id
            WHERE m.plate_number = :plate_number {time_filter_clauses['maintenance']}
            ORDER BY m.request_time DESC
        """, params).fetchall()

        # 5. (新增) 计算违章在部门内的排名 (此项统计通常基于全部历史数据，不受时间筛选影响)
        violation_rank_query = """
            WITH DepartmentViolations AS (
                SELECT 
                    v.plate_number,
                    COUNT(i.violation_id) as violation_count
                FROM vehicles v
                LEFT JOIN violations i ON v.plate_number = i.plate_number
                WHERE v.department_id = ?
                GROUP BY v.plate_number
            )
            SELECT plate_number, violation_count, RANK() OVER (ORDER BY violation_count DESC) as rank
            FROM DepartmentViolations
        """
        dept_violations = conn.execute(violation_rank_query, (department_id,)).fetchall()
        
        violation_rank_info = {
            'rank': 0,
            'total_vehicles': len(dept_violations)
        }
        for row in dept_violations:
            if row['plate_number'] == plate_number:
                violation_rank_info['rank'] = row['rank']
                break
        
        conn.close()
        
        # --- 数据聚合与格式化 ---
        
        # 里程聚合
        total_distance = sum(r['distance_driven'] for r in fuel_mileage_details)
        mileage_trend = {
            'labels': [r['month'] for r in fuel_mileage_details],
            'data': [r['distance_driven'] for r in fuel_mileage_details]
        }
        
        # 油耗聚合
        total_fuel = sum(r['total_fuel_amount'] for r in fuel_mileage_details)
        total_fuel_cost = sum(r['total_fuel_cost'] for r in fuel_mileage_details)
        avg_consumption = (total_fuel / total_distance * 100) if total_distance > 0 else 0
        fuel_trend = {
            'labels': [r['month'] for r in fuel_mileage_details],
            'data': [r['total_fuel_amount'] for r in fuel_mileage_details]
        }

        # 违章聚合
        violation_trend_data = {}
        for row in violation_details:
            month = row['violation_time'][:7] # YYYY-MM
            violation_trend_data[month] = violation_trend_data.get(month, 0) + 1
        sorted_v_trend = sorted(violation_trend_data.items())
        violation_trend = {
            'labels': [item[0] for item in sorted_v_trend],
            'data': [item[1] for item in sorted_v_trend]
        }

        # 维保聚合
        maintenance_months = [r['request_time'][:10] for r in maintenance_details]
        total_maintenance_months = (pd.to_datetime(max(maintenance_months)) - pd.to_datetime(min(maintenance_months))).days / 30.44 if maintenance_months else 1
        total_maintenance_months = max(total_maintenance_months, 1)

        total_maintenance_cost = sum(r['maintenance_cost'] for r in maintenance_details)
        avg_monthly_cost = total_maintenance_cost / total_maintenance_months if total_maintenance_months > 0 else 0

        # --- 构造最终响应 ---
        response_data = {
            'basic_info': basic_info_dict,
            'mileage': {
                'total_distance': total_distance,
                'trend': mileage_trend,
                'details': [dict(r) for r in fuel_mileage_details]
            },
            'fuel': {
                'total_fuel': total_fuel,
                'total_fuel_cost': total_fuel_cost,
                'avg_consumption': avg_consumption,
                'trend': fuel_trend,
                'details': [dict(r) for r in fuel_mileage_details]
            },
            'violations': {
                'total_count': len(violation_details),
                'rank_info': violation_rank_info,
                'trend': violation_trend,
                'details': [dict(r) for r in violation_details]
            },
            'maintenance': {
                'total_count': len(maintenance_details),
                'total_cost': total_maintenance_cost,
                'avg_monthly_cost': avg_monthly_cost,
                'details': [dict(r) for r in maintenance_details]
            }
        }

        return jsonify(response_data)

    except sqlite3.Error as e:
        return jsonify({"error": f"数据库错误: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"发生意外错误: {e}"}), 500


# (新增) ===============================================
#       图片上传及服务相关 API
# =====================================================

def allowed_file(filename):
    """检查文件扩展名是否在允许的范围内"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/vehicle_images/<filename>')
def uploaded_file(filename):
    """为上传的文件提供访问服务"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/vehicle/upload_image/<plate_number>', methods=['POST'])
def upload_vehicle_image(plate_number):
    """处理车辆图片的上传"""
    if 'file' not in request.files:
        return jsonify(error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error='No selected file'), 400
    if file and allowed_file(file.filename):
        # (修改) 使用更安全的文件名生成方式
        ext = file.filename.rsplit('.', 1)[1].lower()
        # 使用 plate_number 和一个唯一的 uuid 来确保文件名不重复
        filename = secure_filename(f"{plate_number}_{uuid.uuid4().hex}.{ext}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # (修改) 更新数据库中 vehicles 表的 image_url 字段
        conn = get_db_connection()
        conn.execute('UPDATE vehicles SET image_url = ? WHERE plate_number = ?', (filename, plate_number))
        conn.commit()
        conn.close()

        # 返回新上传文件的完整 URL
        image_url = url_for('uploaded_file', filename=filename, _external=True)
        return jsonify(imageUrl=image_url)

    return jsonify(error='File type not allowed'), 400


# (新增) ===============================================
#       部门详情页面的 API 端点
# =====================================================
@app.route('/api/department/detail/<int:department_id>', methods=['GET'])
def get_department_detail(department_id):
    """
    API 端点，获取单个部门的详细信息，用于部门详情页。
    支持 start_month 和 end_month URL参数进行时间范围过滤。
    """
    try:
        start_month = request.args.get('start_month')
        end_month = request.args.get('end_month')

        conn = get_db_connection()

        # 1. 查询部门基本信息
        department_info = conn.execute('SELECT * FROM departments WHERE department_id = ?', (department_id,)).fetchone()
        if not department_info:
            return jsonify(error="Department not found"), 404

        # 2. 准备时间筛选条件
        params = {'department_id': department_id}
        where_clauses = {}
        if start_month and end_month:
            params.update({'start': f'{start_month}-01', 'end': f'{end_month}-31'})
            where_clauses['fuel'] = "AND date(s.year || '-' || printf('%02d', s.month) || '-01') BETWEEN date(:start) AND date(:end)"
            where_clauses['violation'] = "AND date(i.violation_time) BETWEEN date(:start) AND date(:end)"
            where_clauses['maint'] = "AND date(m.request_time) BETWEEN date(:start) AND date(:end)"

        # 3. 查询部门内的车辆列表
        vehicles_in_dept = conn.execute("""
            SELECT vehicle_id, plate_number, brand_model, manager 
            FROM vehicles WHERE department_id = ?
        """, (department_id,)).fetchall()
        
        # 4. 聚合部门KPI和月度趋势
        kpis = {'vehicle_count': len(vehicles_in_dept)}
        trends = {}
        
        # 里程和油耗
        fuel_mileage_q = conn.execute(f"""
            SELECT 
                SUM(s.distance_driven) as total_distance, SUM(s.total_fuel_amount) as total_fuel,
                s.year || '-' || printf('%02d', s.month) as month
            FROM monthly_fuel_summary s JOIN vehicles v ON s.plate_number = v.plate_number
            WHERE v.department_id = :department_id {where_clauses.get('fuel', '')}
            GROUP BY month ORDER BY month
        """, params).fetchall()
        kpis['total_distance'] = sum(r['total_distance'] for r in fuel_mileage_q)
        kpis['total_fuel'] = sum(r['total_fuel'] for r in fuel_mileage_q)
        trends['mileage'] = {'labels': [r['month'] for r in fuel_mileage_q], 'data': [r['total_distance'] for r in fuel_mileage_q]}
        trends['fuel'] = {'labels': [r['month'] for r in fuel_mileage_q], 'data': [r['total_fuel'] for r in fuel_mileage_q]}

        # 违章
        violations_q = conn.execute(f"""
            SELECT COUNT(i.violation_id) as count, strftime('%Y-%m', i.violation_time) as month
            FROM violations i JOIN vehicles v ON i.plate_number = v.plate_number
            WHERE v.department_id = :department_id {where_clauses.get('violation', '')}
            GROUP BY month ORDER BY month
        """, params).fetchall()
        kpis['violation_count'] = sum(r['count'] for r in violations_q)
        trends['violations'] = {'labels': [r['month'] for r in violations_q], 'data': [r['count'] for r in violations_q]}
        
        # 维保
        maint_q = conn.execute(f"""
            SELECT SUM(m.maintenance_cost) as total_cost, strftime('%Y-%m', m.request_time) as month
            FROM maintenance m JOIN vehicles v ON m.plate_number = v.plate_number
            WHERE v.department_id = :department_id {where_clauses.get('maint', '')}
            GROUP BY month ORDER BY month
        """, params).fetchall()
        kpis['maintenance_cost'] = sum(r['total_cost'] for r in maint_q)
        trends['maintenance'] = {'labels': [r['month'] for r in maint_q], 'data': [r['total_cost'] for r in maint_q]}

        # 5. 查询部门内车辆排名
        rankings = {}
        vehicle_plate_numbers = [v['plate_number'] for v in vehicles_in_dept]
        if vehicle_plate_numbers:
            # 排名查询 (构建 IN 子句)
            in_clause = ','.join('?' for _ in vehicle_plate_numbers)
            
            # 里程排名
            mileage_rank = conn.execute(f"""
                SELECT s.plate_number, SUM(s.distance_driven) as value
                FROM monthly_fuel_summary s
                WHERE s.plate_number IN ({in_clause}) {where_clauses.get('fuel', '').replace('s.','')}
                GROUP BY s.plate_number ORDER BY value DESC
            """, vehicle_plate_numbers + (list(params.values())[1:] if 'start' in params else []) ).fetchall()
            rankings['mileage'] = [dict(r) for r in mileage_rank]
            
            # 违章排名
            violation_rank = conn.execute(f"""
                SELECT i.plate_number, COUNT(i.violation_id) as value
                FROM violations i
                WHERE i.plate_number IN ({in_clause}) {where_clauses.get('violation', '').replace('i.','')}
                GROUP BY i.plate_number ORDER BY value DESC
            """, vehicle_plate_numbers + (list(params.values())[1:] if 'start' in params else [])).fetchall()
            rankings['violations'] = [dict(r) for r in violation_rank]

        conn.close()

        return jsonify({
            'department_info': dict(department_info),
            'kpis': kpis,
            'trends': trends,
            'rankings': rankings,
            'vehicles': [dict(v) for v in vehicles_in_dept]
        })

    except Exception as e:
        return jsonify(error=f"An unexpected error occurred: {e}"), 500


@app.route('/api/search', methods=['GET'])
def search():
    """
    API 端点，用于全局搜索部门和车辆。
    接收一个查询参数 'q'。
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    try:
        conn = get_db_connection()

        # 搜索部门 (限制5条结果)
        departments_query = """
            SELECT department_id, name
            FROM departments
            WHERE name LIKE ?
            LIMIT 5
        """
        departments = conn.execute(departments_query, (f'%{query}%',)).fetchall()

        # 搜索车辆 (限制5条结果)
        vehicles_query = """
            SELECT plate_number
            FROM vehicles
            WHERE plate_number LIKE ?
            LIMIT 5
        """
        vehicles = conn.execute(vehicles_query, (f'%{query}%',)).fetchall()

        conn.close()

        # 格式化并合并结果
        results = []
        for dept in departments:
            results.append({
                'type': 'department',
                'id': dept['department_id'],
                'name': dept['name']
            })
        for vehicle in vehicles:
            results.append({
                'type': 'vehicle',
                'id': vehicle['plate_number'],
                'name': vehicle['plate_number']
            })

        return jsonify(results)

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
