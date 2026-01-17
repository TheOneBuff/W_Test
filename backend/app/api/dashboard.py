from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..database import get_db
from .. import models

router = APIRouter()


@router.get("/trend")
def get_case_trend(days: int = 7, db: Session = Depends(get_db)):
    # 1. 生成日期列表
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days + 1)]

    # 2. 查询数据: 按项目、日期分组统计
    # [修复] 使用 func.date() 代替 func.date_format() 以兼容 SQLite 和 MySQL
    date_col = func.date(models.TestCase.create_time)

    results = db.query(
        models.TestCase.project_id,
        date_col.label('date'),
        func.count(models.TestCase.id)
    ).filter(
        models.TestCase.create_time >= start_date
    ).group_by(
        models.TestCase.project_id, date_col
    ).all()

    # 3. 数据处理: 转为 ECharts 格式
    # 获取所有涉及的项目名称
    project_ids = set([r[0] for r in results if r[0]])
    projects = db.query(models.Project).filter(models.Project.id.in_(project_ids)).all()
    p_map = {p.id: p.name for p in projects}

    series = []

    # 对每个项目生成一条线
    for pid, pname in p_map.items():
        data = []
        for d in date_list:
            # 查找该项目在该日的数量，没找到填 0
            # 注意：SQLite 返回的 date 可能是字符串，MySQL 可能是 date 对象，统一转字符串比较
            count = next((r[2] for r in results if r[0] == pid and str(r[1]) == d), 0)
            data.append(count)

        series.append({
            "name": pname,
            "data": data
        })

    return {
        "dates": date_list,
        "series": series
    }