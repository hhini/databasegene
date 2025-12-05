from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import pandas as pd

# 1. 初始化 APP
app = FastAPI(title="生信基因查询平台", version="1.0")

# 2. 数据库连接配置 (连接池模式)
# 真实公司里，这个 URL 通常放在环境变量里，不写死在代码里
#DB_URL = "postgresql+psycopg2://bio_admin:bio12345@localhost/omics_db"
DB_URL = "postgresql+psycopg2://bio_admin:bio12345@172.17.0.1/omics_db"
engine = create_engine(DB_URL, pool_size=5, max_overflow=10)

# 3. 定义根目录，打个招呼
@app.get("/")
def read_root():
    return {"message": "欢迎使用基因组数据库 API，请访问 /get_gene 进行查询"}

# 4. 核心接口：查询基因详情
# 访问地址例子: http://IP/get_gene?name=TP53
@app.get("/get_gene")
def get_gene_info(name: str):
    """
    输入 gene_symbol (例如 BRCA1, TP53)，返回该基因的详细信息及在各样本中的表达量
    """
    
    # 将输入的基因名转为大写（防止用户输小写查不到）
    gene_symbol = name.upper() 

    # 编写 SQL：这是一个三表联合查询 (Triple Join)
    # genes 表 -> 拿基因描述
    # expression_data 表 -> 拿表达量
    # sample_info 表 -> 拿样本的临床信息 (肺癌还是正常？)
    sql = text("""
        SELECT 
            g.gene_id,
            g.gene_symbol,
            g.description,
            e.tpm_value,
            s.sample_id,
            s.tissue_type,
            s.condition
        FROM genes g
        JOIN expression_data e ON g.gene_id = e.gene_id
        JOIN sample_info s ON e.sample_id = s.sample_id
        WHERE g.gene_symbol LIKE :symbol
    """)

    try:
        # 建立连接并查询
        with engine.connect() as conn:
            # 使用模糊查询 (LIKE)，加上 % 允许部分匹配
            # 如果你想要精确匹配，把上面的 LIKE 改成 =，下面的 f"%{gene_symbol}%" 改成 gene_symbol
            result = conn.execute(sql, {"symbol": f"%{gene_symbol}%"})
            rows = result.fetchall()

        # 如果没查到数据
        if not rows:
            return {"status": "error", "message": f"未找到名为 {gene_symbol} 的基因数据"}

        # 整理数据返回 JSON
        # 我们把每一行结果转换成字典
        data_list = []
        for row in rows:
            data_list.append({
                "gene_id": row.gene_id,
                "symbol": row.gene_symbol,
                "description": row.description,
                "expression_tpm": float(row.tpm_value),
                "sample_info": {
                    "id": row.sample_id,
                    "tissue": row.tissue_type,
                    "condition": row.condition
                }
            })

        return {
            "status": "success", 
            "query_gene": gene_symbol,
            "results_count": len(data_list),
            "data": data_list
        }

    except Exception as e:
        # 如果数据库崩了或者 SQL 写错了，返回 500 错误
        raise HTTPException(status_code=500, detail=str(e))