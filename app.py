import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# ==============================================================================
# 1. 🎨 页面基础配置 (Page Config)
# ==============================================================================
st.set_page_config(
    page_title="OmicsCloud 基因数据平台",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义一些 CSS 让页面更精致
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    h1 {color: #2c3e50;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px #ddd;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 🔌 数据库连接 (Database Connection) - 带缓存优化
# ==============================================================================
# ==============================================================================
# 2. 🔌 数据库连接 (Database Connection) - 带缓存优化
# ==============================================================================
@st.cache_resource(ttl=3600)  # 缓存连接1小时
def get_db_engine():
    try:
        # 👇 这里！把你的 Neon 连接串直接贴在这里
        # 注意：开头是 postgresql:// 
        db_url = "postgresql://neondb_owner:npg_KracX4hO7jAf@ep-falling-bird-a4m0z2kx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
        
        # 创建连接引擎
        engine = create_engine(db_url)
        
        # 测试连接
        with engine.connect() as conn:
            pass
        return engine
    except Exception as e:
        st.error(f"⚠️ 数据库连接失败: {e}")
        return None

# ==============================================================================
# 3. 🔍 侧边栏 (Sidebar) - 控制区
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dna-helix.png", width=80)
    st.title("OmicsCloud 🧬")
    st.caption("基于 Neon Serverless Postgres")
    st.markdown("---")
    
    st.header("🔎 检索条件")
    search_gene = st.text_input("输入基因符号 (Gene Symbol)", value="TP53", help="支持模糊搜索，例如 'BRCA'").strip().upper()
    
    # 高级过滤器
    st.markdown("### ⚙️ 筛选器")
    filter_tissue = st.selectbox("组织类型 (Tissue)", ["All", "Lung", "Liver", "Blood"], index=0)
    
    search_btn = st.button("开始分析", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.info("💡 **提示**: \n数据来源于模拟的高通量测序流程 (ETL)。\n后端采用 Python SQLAlchemy 进行连接。")

# ==============================================================================
# 4. 🚀 主逻辑区 (Main Logic)
# ==============================================================================

if not engine:
    st.warning("请先在 Streamlit Cloud 后台配置数据库连接串 (Secrets)！")
    st.stop()

st.title("🧬 基因表达量多维分析系统")
st.markdown(f"当前检索目标：**{search_gene}**")

if search_btn or search_gene:
    with st.spinner("🚀 正在云端数据库检索数万条记录..."):
        try:
            # A. 核心 SQL 查询 (Triple Join)
            # 根据用户是否筛选组织，动态调整 SQL
            sql_base = """
                SELECT 
                    g.gene_id, g.gene_symbol, g.description, g.chromosome,
                    e.tpm_value, e.sequencing_date,
                    s.sample_id, s.tissue_type, s.condition, s.patient_age
                FROM genes g
                JOIN expression_data e ON g.gene_id = e.gene_id
                JOIN sample_info s ON e.sample_id = s.sample_id
                WHERE g.gene_symbol LIKE :gene_name
            """
            
            params = {"gene_name": f"%{search_gene}%"}
            
            if filter_tissue != "All":
                sql_base += " AND s.tissue_type = :tissue"
                params["tissue"] = filter_tissue
                
            sql_base += " ORDER BY e.tpm_value DESC LIMIT 500"

            # 执行查询
            with engine.connect() as conn:
                df = pd.read_sql(text(sql_base), conn, params=params)

            # B. 结果展示逻辑
            if df.empty:
                st.warning(f"⚠️ 未找到名为 `{search_gene}` 的基因数据 (或该组织下无表达)。")
            else:
                # 获取基因的基本信息 (取第一行)
                meta = df.iloc[0]
                
                # --- 第一部分：关键指标 (KPIs) ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("基因 ID", meta['gene_id'])
                col2.metric("所在染色体", meta['chromosome'])
                col3.metric("最高表达量 (TPM)", f"{df['tpm_value'].max():.2f}")
                col4.metric("平均表达量 (TPM)", f"{df['tpm_value'].mean():.2f}")
                
                st.markdown("### 📜 基因描述")
                st.info(meta['description'])

                # --- 第二部分：多维视图 (Tabs) ---
                tab1, tab2, tab3 = st.tabs(["📊 可视化分析", "📋 详细数据表", "📥 导出报告"])

                with tab1:
                    # 1. 表达量分布 (箱线图)
                    st.subheader("不同疾病状态下的表达量分布")
                    fig_box = px.box(
                        df, 
                        x="condition", 
                        y="tpm_value", 
                        color="tissue_type",
                        points="all",
                        hover_data=["sample_id", "patient_age"],
                        title=f"{meta['gene_symbol']} Expression by Condition",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_box, use_container_width=True)
                    
                    # 2. 样本柱状图
                    st.subheader("各样本表达量对比")
                    fig_bar = px.bar(
                        df, 
                        x="sample_id", 
                        y="tpm_value", 
                        color="tissue_type",
                        text_auto='.1f',
                        title="TPM Value per Sample"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with tab2:
                    st.subheader("样本详细列表")
                    # 使用 Pandas Styler 高亮高表达
                    st.dataframe(
                        df[["sample_id", "tissue_type", "condition", "tpm_value", "patient_age", "sequencing_date"]],
                        use_container_width=True,
                        column_config={
                            "tpm_value": st.column_config.NumberColumn(
                                "TPM Expression",
                                help="Transcripts Per Million",
                                format="%.2f"
                            )
                        }
                    )
                
                with tab3:
                    st.subheader("数据导出")
                    st.write("将当前筛选结果导出为 CSV 文件用于后续分析。")
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ 下载 CSV 报告",
                        data=csv,
                        file_name=f"{search_gene}_report.csv",
                        mime="text/csv",
                    )

        except Exception as e:
            st.error(f"❌ 系统发生错误: {e}")
            st.code(sql_base) # 调试时显示 SQL，生产环境可去掉

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Developed with ❤️ by BioInfo Engineer | Powered by <b>Neon Serverless Postgres</b> & <b>Streamlit</b>
    </div>
    """, 
    unsafe_allow_html=True
)