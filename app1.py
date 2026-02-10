import streamlit as st
import plotly.express as px
import pandas as pd
import random
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 初始化设置 ---
st.set_page_config(
    page_title="Ph.D. Nexus | 博士学术联合体",
    page_icon="🎓",
    layout="wide"
)


# --- 2. 数据库连接模块 (核心) ---
def get_connection():
    # ttl=0 表示不做缓存，每次都强制从 Google 拉取最新数据
    return st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet_name):
    """读取指定工作表的数据"""
    conn = get_connection()
    try:
        # 尝试读取数据
        df = conn.read(worksheet=worksheet_name, ttl=0)
        # 如果是空的或者列名不对，返回空DataFrame但保留列结构
        if worksheet_name == "posts" and df.empty:
            return pd.DataFrame(columns=["username", "content", "category", "time", "likes", "avatar_seed"])
        return df
    except Exception:
        return pd.DataFrame()


def save_post_to_cloud(username, content, category):
    """保存帖子到云端"""
    conn = get_connection()
    df = get_data("posts")

    new_data = pd.DataFrame([{
        "username": username,
        "content": content,
        "category": category,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "likes": 0,
        "avatar_seed": str(random.randint(1000, 9999))
    }])

    # 合并并更新
    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(worksheet="posts", data=updated_df)


def update_config_cloud(key, value):
    """发起人修改配置"""
    conn = get_connection()
    df = get_data("config")

    # 查找并更新，或者新增
    if key in df['key'].values:
        df.loc[df['key'] == key, 'value'] = value
    else:
        new_row = pd.DataFrame([{"key": key, "value": value}])
        df = pd.concat([df, new_row], ignore_index=True)

    conn.update(worksheet="config", data=df)


def get_config_value(key, default_text):
    """获取配置信息"""
    df = get_data("config")
    if df.empty: return default_text
    res = df[df['key'] == key]
    if not res.empty:
        return res.iloc[0]['value']
    return default_text


# --- 3. 样式美化 ---
def apply_style():
    st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .paper-card {
        background: white; padding: 20px; border-radius: 10px;
        border-left: 5px solid #2c3e50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    h1, h2, h3 { font-family: 'Times New Roman', serif; }
    </style>
    """, unsafe_allow_html=True)


# --- 4. 页面逻辑 ---
def main():
    apply_style()

    # --- 侧边栏：发起人控制台 ---
    st.sidebar.title("🏛️ Ph.D. Nexus")

    # 从云端获取最新的发起人信息
    founder_name = get_config_value("founder_name", "Dr. Unknown")
    announcement = get_config_value("announcement", "暂无公告")

    st.sidebar.markdown("---")
    st.sidebar.info(f"**发起人**: {founder_name}")

    # 管理员登录逻辑
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        with st.sidebar.expander("🔑 发起人登录"):
            pwd = st.text_input("Access Token", type="password")
            if st.button("Login"):
                if pwd == "phd2024":  # 这里设置你的管理员密码
                    st.session_state.is_admin = True
                    st.rerun()
    else:
        st.sidebar.success("管理员模式已激活")
        if st.sidebar.button("退出管理"):
            st.session_state.is_admin = False
            st.rerun()

        st.sidebar.markdown("### ⚙️ 实时修改")
        with st.sidebar.form("admin_form"):
            new_founder = st.text_input("修改发起人姓名", founder_name)
            new_announce = st.text_input("修改全站公告", announcement)
            if st.form_submit_button("更新并同步至云端"):
                update_config_cloud("founder_name", new_founder)
                update_config_cloud("announcement", new_announce)
                st.success("更新成功！")
                time.sleep(1)
                st.rerun()

    # --- 主页面 ---
    menu = st.sidebar.radio("导航", ["大厅 (Lobby)", "研讨会 (Colloquium)", "能力雷达 (Radar)"])

    if menu == "大厅 (Lobby)":
        st.title("Ph.D. Nexus Ecosystem")
        st.markdown(f"> 📢 **公告**: {announcement}")

        st.markdown("### 📊 社区概览")
        df = get_data("posts")
        c1, c2 = st.columns(2)
        c1.metric("累计文献探讨", len(df) if not df.empty else 0)
        c2.metric("当前活跃度", "High")

    elif menu == "研讨会 (Colloquium)":
        st.subheader("💬 学术研讨")

        with st.expander("➕ 发起新的讨论"):
            with st.form("post_form", clear_on_submit=True):
                u_name = st.text_input("Researcher ID")
                u_cat = st.selectbox("类型", ["Methodology", "Experiment", "Review"])
                u_content = st.text_area("摘要 / 观点")
                if st.form_submit_button("Submit"):
                    if u_name and u_content:
                        save_post_to_cloud(u_name, u_content, u_cat)
                        st.success("已写入云端数据库！")
                        st.rerun()

        # 展示帖子
        df = get_data("posts")
        if not df.empty:
            # 倒序排列，最新的在前面
            df = df.sort_index(ascending=False)
            for i, row in df.iterrows():
                avatar = f"https://api.dicebear.com/9.x/initials/svg?seed={row['avatar_seed']}"
                c1, c2 = st.columns([1, 10])
                with c1: st.image(avatar, width=50)
                with c2:
                    st.markdown(f"""
                    <div class="paper-card">
                        <small>{row['time']} | {row['category']}</small>
                        <h4>{row['username']}</h4>
                        <p>{row['content']}</p>
                    </div>
                    """, unsafe_allow_html=True)

    elif menu == "能力雷达 (Radar)":
        st.subheader("⚖️ 科研五维评估")
        c1, c2 = st.columns([1, 2])
        with c1:
            v1 = st.slider("Coding", 0, 10, 5)
            v2 = st.slider("Writing", 0, 10, 5)
            v3 = st.slider("Reading", 0, 10, 5)
            v4 = st.slider("Math", 0, 10, 5)
            v5 = st.slider("Mental", 0, 10, 5)
        with c2:
            data = pd.DataFrame(dict(
                r=[v1, v2, v3, v4, v5],
                theta=['Coding', 'Writing', 'Reading', 'Math', 'Mental']
            ))
            fig = px.line_polar(data, r='r', theta='theta', line_close=True)
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
            st.plotly_chart(fig)


if __name__ == "__main__":
    main()