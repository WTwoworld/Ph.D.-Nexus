import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import random
import time
import base64
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 全局与配置 ---
st.set_page_config(
    page_title="Ph.D. Nexus | 全球学术联合体",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认收起侧边栏，突出封面
)


# --- 2. 核心逻辑与数据库 ---
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet_name):
    conn = get_connection()
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        # 确保列存在，防止报错
        if worksheet_name == "posts":
            required_cols = ["username", "content", "category", "time", "likes", "avatar_seed", "filename", "file_type",
                             "file_data"]
            # 如果是空表，初始化结构
            if df.empty:
                return pd.DataFrame(columns=required_cols)
            # 填充缺失列（兼容旧数据）
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None
        return df
    except Exception:
        return pd.DataFrame()


def save_post_with_file(username, content, category, uploaded_file):
    conn = get_connection()
    df = get_data("posts")

    # 处理文件上传 (Base64编码)
    f_name, f_type, f_data = None, None, None
    if uploaded_file is not None:
        try:
            # 限制大小：Google Sheets 单元格有字符限制，这里限制 500KB 以内的小文件
            if uploaded_file.size > 500 * 1024:
                st.error("⚠️ 文件过大！为保证云端表格稳定性，请上传 500KB 以内的文件 (如摘要PDF、图片)。")
                return False

            f_name = uploaded_file.name
            f_type = uploaded_file.type
            # 将文件转为 Base64 字符串存储
            bytes_data = uploaded_file.getvalue()
            f_data = base64.b64encode(bytes_data).decode()
        except Exception as e:
            st.error(f"文件处理失败: {e}")
            return False

    new_data = pd.DataFrame([{
        "username": username,
        "content": content,
        "category": category,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "likes": 0,
        "avatar_seed": str(random.randint(1000, 9999)),
        "filename": f_name,
        "file_type": f_type,
        "file_data": f_data
    }])

    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(worksheet="posts", data=updated_df)
    return True


def update_likes(index, current_likes):
    conn = get_connection()
    df = get_data("posts")
    df.at[index, "likes"] = int(current_likes) + 1
    conn.update(worksheet="posts", data=df)


def update_config_cloud(key, value):
    conn = get_connection()
    df = get_data("config")
    if key in df['key'].values:
        df.loc[df['key'] == key, 'value'] = value
    else:
        new_row = pd.DataFrame([{"key": key, "value": value}])
        df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="config", data=df)


def get_config_value(key, default_text):
    df = get_data("config")
    if df.empty: return default_text
    res = df[df['key'] == key]
    return res.iloc[0]['value'] if not res.empty else default_text


# --- 3. 视觉工程 (CSS) ---
def apply_style():
    st.markdown("""
    <style>
    /* 全局字体与背景 */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap');

    .stApp {
        background-color: #f8fafc;
        font-family: 'Lato', sans-serif;
    }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        color: white;
    }

    /* 封面 Hero Section */
    .hero-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        padding: 80px 40px;
        border-radius: 0 0 40px 40px;
        text-align: center;
        color: white;
        margin-bottom: 40px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }

    .hero-title {
        font-family: 'Cinzel', serif;
        font-size: 4em;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 10px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }

    .hero-subtitle {
        font-size: 1.2em;
        opacity: 0.8;
        font-weight: 300;
        max-width: 600px;
        margin: 0 auto;
    }

    /* 卡片设计 */
    .post-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .post-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        border-color: #3b82f6;
    }

    /* 标签 */
    .tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        background: #eff6ff;
        color: #2563eb;
        font-size: 0.8rem;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    /* 装饰元素 */
    .divider {
        height: 4px;
        width: 60px;
        background: #fbbf24; /* 金色 */
        margin: 20px auto;
        border-radius: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


# --- 4. 页面组件 ---

def show_hero_section(announcement):
    """渲染大气磅礴的封面"""
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Ph.D. NEXUS</div>
        <div class="divider"></div>
        <p class="hero-subtitle">Connecting Minds, Advancing Science.<br>Standing on the shoulders of giants.</p>
        <div style="margin-top: 30px; background: rgba(255,255,255,0.1); display: inline-block; padding: 10px 20px; border-radius: 8px; backdrop-filter: blur(5px);">
            📢 <b>Notice:</b> {announcement}
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_stats_dashboard(df):
    """数据可视化看板"""
    if df.empty: return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 文献库", f"{len(df)}", "Papers")
    c2.metric("🔥 讨论热度", f"{df['likes'].sum()}", "Likes")
    c3.metric("👥 活跃学者", f"{df['username'].nunique()}", "Researchers")
    c4.metric("📁 共享文件", f"{df['filename'].notnull().sum()}", "Files")

    # 趋势图
    st.markdown("### 📈 学术趋势 (Trend Analysis)")

    # 简单的按时间统计
    df['date'] = pd.to_datetime(df['time']).dt.date
    daily_counts = df.groupby('date').size().reset_index(name='counts')

    fig = px.area(daily_counts, x='date', y='counts', title=None,
                  color_discrete_sequence=['#3b82f6'])
    fig.update_layout(xaxis_title="", yaxis_title="Posts", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)


def show_file_download(row):
    """处理 Base64 文件下载"""
    if row['filename'] and row['file_data']:
        try:
            b64_data = row['file_data']
            file_bytes = base64.b64decode(b64_data)

            st.download_button(
                label=f"📎 下载附件: {row['filename']}",
                data=file_bytes,
                file_name=row['filename'],
                mime=row['file_type'],
                key=f"dl_{row.name}"
            )
        except:
            st.error("文件解析错误")


# --- 5. 主程序 ---
def main():
    apply_style()

    # 获取配置
    founder = get_config_value("founder_name", "Academic Board")
    announcement = get_config_value("announcement", "Welcome to the future of research.")

    # 渲染封面
    show_hero_section(announcement)

    # 导航栏（使用 Tabs 代替 Radio，更现代）
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🏛️ 学术广场 (Forum)", "📊 数据洞察 (Insights)", "⚖️ 能力雷达 (Radar)", "⚙️ 管理中心 (Admin)"])

    # --- Tab 1: 论坛 (带文件上传) ---
    with tab1:
        c_left, c_right = st.columns([2, 1])

        with c_right:
            st.markdown("### ✍️ 发表成果 (Submit)")
            with st.container(border=True):
                with st.form("new_post", clear_on_submit=True):
                    u_name = st.text_input("Scholar ID")
                    u_cat = st.selectbox("Category", ["Computer Science", "Biology", "Physics", "Social Science"])
                    u_content = st.text_area("Abstract / Insight", height=150)
                    u_file = st.file_uploader("Upload File (Max 500KB)", type=['pdf', 'png', 'jpg', 'py', 'txt'])

                    if st.form_submit_button("🚀 Publish to Nexus"):
                        if u_name and u_content:
                            success = save_post_with_file(u_name, u_content, u_cat, u_file)
                            if success:
                                st.success("Published Successfully!")
                                time.sleep(1)
                                st.rerun()

        with c_left:
            st.markdown("### 🔍 探索 (Discover)")
            search_term = st.text_input("Search keywords...", placeholder="Try 'Mamba' or 'Transformer'")

            df = get_data("posts")
            if not df.empty:
                df = df.sort_index(ascending=False)

                # 搜索过滤
                if search_term:
                    df = df[
                        df['content'].str.contains(search_term, case=False) | df['username'].str.contains(search_term,
                                                                                                          case=False)]

                for i, row in df.iterrows():
                    avatar = f"https://api.dicebear.com/9.x/initials/svg?seed={row['avatar_seed']}"

                    col_img, col_txt = st.columns([1, 8])
                    with col_img:
                        st.image(avatar, width=50)
                    with col_txt:
                        st.markdown(f"""
                        <div class="post-card">
                            <div style="display:flex; justify-content:space-between;">
                                <span class="tag">{row['category']}</span>
                                <span style="color:#94a3b8; font-size:0.8em;">{row['time']}</span>
                            </div>
                            <h4 style="margin: 10px 0; color: #1e293b;">{row['username']}</h4>
                            <p style="color: #475569; line-height: 1.6;">{row['content']}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # 操作栏
                        ac1, ac2 = st.columns([1, 4])
                        with ac1:
                            if st.button(f"❤️ {row['likes']}", key=f"like_{i}"):
                                update_likes(i, row['likes'])
                                st.rerun()
                        with ac2:
                            show_file_download(row)

    # --- Tab 2: 数据洞察 ---
    with tab2:
        df = get_data("posts")
        show_stats_dashboard(df)

        st.markdown("---")
        st.markdown("### 🌪️ 关键词分布")
        if not df.empty:
            cat_counts = df['category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            fig_pie = px.pie(cat_counts, values='Count', names='Category', hole=0.4,
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- Tab 3: 能力雷达 ---
    with tab3:
        st.markdown("### 🧬 Scholar Attribute System")
        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            with st.container(border=True):
                st.write("Current Status:")
                math = st.slider("Math", 0, 100, 70)
                code = st.slider("Code", 0, 100, 60)
                write = st.slider("Write", 0, 100, 50)
                read = st.slider("Read", 0, 100, 80)
                idea = st.slider("Novelty", 0, 100, 60)

        with col_r2:
            data = pd.DataFrame(dict(
                r=[math, code, write, read, idea],
                theta=['Math', 'Code', 'Write', 'Read', 'Novelty']
            ))
            fig = px.line_polar(data, r='r', theta='theta', line_close=True)
            fig.update_traces(fill='toself', line_color='#1e3a8a')
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # --- Tab 4: 管理后台 ---
    with tab4:
        st.header("⚙️ Admin Control")

        # 登录校验
        if "is_admin" not in st.session_state: st.session_state.is_admin = False

        if not st.session_state.is_admin:
            pwd = st.text_input("Admin Token", type="password")
            if st.button("Verify Identity"):
                if pwd == "phd2024":
                    st.session_state.is_admin = True
                    st.rerun()
        else:
            st.success(f"Welcome back, {founder}")

            with st.form("admin_settings"):
                st.subheader("Global Settings")
                new_founder = st.text_input("Founder Name", founder)
                new_ann = st.text_input("Global Announcement", announcement)

                if st.form_submit_button("Update System"):
                    update_config_cloud("founder_name", new_founder)
                    update_config_cloud("announcement", new_ann)
                    st.success("System Updated.")
                    time.sleep(1)
                    st.rerun()

            if st.button("Log Out"):
                st.session_state.is_admin = False
                st.rerun()

    # 底部页脚
    st.markdown("""
    <div style="text-align: center; margin-top: 50px; color: #94a3b8; font-size: 0.8em;">
        &copy; 2024 Ph.D. Nexus | Built with Streamlit & Python | Powered by Google Cloud
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
