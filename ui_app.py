import streamlit as st
import requests
import pandas as pd

# 🎨 1. 页面标题和布局
st.set_page_config(page_title="Omics 基因查询平台", page_icon="🧬", layout="wide")

st.title("🧬 公司级基因表达量查询系统")
st.markdown("---")

# 🔍 2. 侧边栏：搜索区
with st.sidebar:
    st.header("🔎 查询条件")
    gene_name = st.text_input("输入基因名称 (Gene Symbol)", "TP53")
    
    # 一个大大的搜索按钮
    search_btn = st.button("开始检索", type="primary")

# 🚀 3. 主逻辑：点击按钮后触发
if search_btn:
    if not gene_name:
        st.warning("请先输入基因名称！")
    else:
        # 显示加载条
        with st.spinner(f"正在数据库中检索 {gene_name} ..."):
            try:
                # ============================================
                # 关键点：前端找后端拿数据 (Call API)
                # 假设你的 FastAPI Docker 正跑在本地的 80 端口
                # ============================================
                api_url = f"http://127.0.0.1:80/get_gene?name={gene_name}"
                response = requests.get(api_url)
                
                # 处理后端返回的 JSON
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("status") == "success":
                        st.success(f"查询成功！共找到 {result['results_count']} 条记录")
                        
                        # --- 数据展示区 ---
                        data_list = result['data']
                        
                        # A. 显示基因基本信息 (拿第一条数据展示即可)
                        first_record = data_list[0]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"**Gene ID:** {first_record['gene_id']}")
                        with col2:
                            st.info(f"**Description:** {first_record['description']}")
                            
                        # B. 构造表格数据
                        # 我们把嵌套的 JSON 拍平，方便用 DataFrame 展示
                        table_rows = []
                        for item in data_list:
                            row = {
                                "样本ID": item['sample_info']['id'],
                                "组织类型": item['sample_info']['tissue'],
                                "疾病状态": item['sample_info']['condition'],
                                "表达量 (TPM)": item['expression_tpm']
                            }
                            table_rows.append(row)
                        
                        df = pd.read_json(pd.io.json.dumps(table_rows), orient='records') # 简单的转换方式
                        # 或者直接 df = pd.DataFrame(table_rows)

                        st.subheader(f"📊 {result['query_gene']} 表达量分布表")
                        st.dataframe(df, use_container_width=True)
                        
                        # C. 画个图 (Streamlit 的强项)
                        st.subheader("📈 表达量可视化")
                        st.bar_chart(df.set_index("样本ID")["表达量 (TPM)"])
                        
                    else:
                        st.error(f"❌ {result.get('message')}")
                else:
                    st.error(f"🔌 连接异常！状态码: {response.status_code}")
                    st.text(f"后端返回详情: {response.text}")
                    
            except Exception as e:
                st.error(f"发生系统错误: {e}")

# 页脚
st.markdown("---")
st.caption("Developed by BioInfo-DevOps Engineer | Tech Stack: FastAPI + Docker + Streamlit + PostgreSQL")