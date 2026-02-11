import streamlit as st
import plotly.express as px
import pandas as pd
import random
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 引入 Google Drive 相关库
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- 1. 全局配置 ---
st.set_page_config(
    page_title="Ph.D. Nexus | 旗舰版",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# --- 2. Google Drive 服务 (新核心) ---
def get_drive_service():
    # 使用 secrets 中的凭据信息来构建 Drive 服务
    scope = ['https://www.googleapis.com/auth/drive']
    # 从 st.secrets 读取之前配置好的 gsheets 信息 (它们是通用的)
    creds_info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=scope
    )
    return build('drive', 'v3', credentials=creds)


def upload_file_to_drive(uploaded_file):
    """将文件上传到 Google Drive 并返回公开链接"""
    try:
        service = get_drive_service()
        folder_id = st.secrets["drive_folder_id"]  # 从配置读取文件夹 ID

        file_metadata = {
            'name': uploaded_file.name,
            'parents': [folder_id]
        }

        media = MediaIoBaseUpload(uploaded_file, mimetype=uploaded_file.type, resumable=True)

        # 执行上传
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # 获取文件链接
        file_link = file.get('webViewLink')

        # (可选) 设置文件为任何人可读，确保其他人能下载
        # 这一步通常需要在 Drive API 权限里允许，如果报错可以注释掉
        try:
            permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(fileId=file.get('id'), body=permission).execute()
        except:
            pass  # 如果服务账号没权限改分享设置，就跳过

        return file_link

    except Exception as e:
        st.error(f"云盘上传失败: {e}")
        return None


# --- 3. 数据库连接 (Google Sheets) ---
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet_name):
    conn = get_connection()
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if worksheet_name == "posts":
            # 兼容旧表结构，确保有这些列
            required = ["username", "content", "category", "time", "likes", "avatar_seed", "filename", "file_link"]
            if df.empty: return pd.DataFrame(columns=required)
            for col in required:
                if col not in df.columns: df[col] = None
        return df
    except:
        return pd.DataFrame()


def save_post_pro(username, content, category, uploaded_file):
    """保存帖子：文件上云盘，数据上表格"""
    conn = get_connection()
    df = get_data("posts")

    file_link = None
    file_name = None

    # 1. 先处理文件上传
    if uploaded_file:
        with st.spinner("正在上传大文件到 Google Drive..."):
            file_link = upload_file_to_drive(uploaded_file)
            file_name = uploaded_file.name
            if not file_link:
                st.error("文件上传失败，请重试")
                return False

    # 2. 再保存元数据到表格
    new_data = pd.DataFrame([{
        "username": username,
        "content": content,
        "category": category,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "likes": 0,
        "avatar_seed": str(random.randint(1000, 9999)),
        "filename": file_name,
        "file_link": file_link  # 存的是链接，不是乱码了！
    }])

    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(worksheet="posts", data=updated_df)
    return True


def update_likes(index, current_likes):
    conn = get_connection()
    df = get_data("posts")
    df.at[index, "likes"] = int(current_likes) + 1
    conn.update(worksheet="posts", data=df)


# --- 配置管理函数 ---
def get_config(key, default):
    df = get_data("config")
    if df.empty: return default
    res = df[df['key'] == key]
    return res.iloc[0]['value'] if not res.empty else default


# --- 4. 界面设计 ---
def apply_style():
    st.markdown("""
    <style>
    .stApp {background: #f8fafc; font-family: 'Helvetica', sans-serif;}
    .hero {
        background: linear-gradient(120deg, #0f172a, #334155); color: white;
        padding: 60px; border-radius: 0 0 30px 30px; text-align: center; margin-bottom: 30px;
    }
    .card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e2e8f0;
    }
    .btn-download {
        text-decoration: none; display: inline-block; padding: 5px 15px;
        background: #eff6ff; color: #2563eb; border-radius: 20px; font-size: 0.8em;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    apply_style()

    # 封面
    announcement = get_config("announcement", "Ph.D. Nexus Pro")
    st.markdown(f"""
    <div class="hero">
        <h1 style="font-size: 3.5em; margin:0;">Ph.D. NEXUS</h1>
        <p style="opacity:0.8; font-size:1.2em;">Enterprise Grade Research Platform</p>
        <div style="margin-top:20px; background:rgba(255,255,255,0.1); display:inline-block; padding:5px 15px; border-radius:20px;">
            🔔 {announcement}
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🏛️ 学术中心", "⚙️ 后台管理"])

    with tab1:
        c1, c2 = st.columns([2, 1])

        # 发布区
        with c2:
            st.markdown("### 📤 上传成果")
            with st.container(border=True):
                with st.form("upload"):
                    u_name = st.text_input("Name")
                    u_cat = st.selectbox("Topic", ["AI", "Bio", "Physics"])
                    u_text = st.text_area("Abstract")
                    # 现在这里不再有大小限制了！
                    u_file = st.file_uploader("Paper / Code (Large files supported)", type=['pdf', 'zip', 'docx', 'py'])

                    if st.form_submit_button("Publish"):
                        if u_name and u_text:
                            if save_post_pro(u_name, u_text, u_cat, u_file):
                                st.success("发布成功！文件已存入 Google Drive。")
                                time.sleep(1)
                                st.rerun()

        # 展示区
        with c1:
            st.markdown("### 📚 最新动态")
            df = get_data("posts")
            if not df.empty:
                df = df.sort_index(ascending=False)
                for i, row in df.iterrows():
                    # 渲染卡片
                    link_html = ""
                    if row['file_link']:
                        link_html = f'<a href="{row["file_link"]}" target="_blank" class="btn-download">📥 下载附件: {row["filename"]}</a>'

                    st.markdown(f"""
                    <div class="card">
                        <div style="display:flex; justify-content:space-between; color:#64748b; font-size:0.8em;">
                            <span>{row['time']} • {row['category']}</span>
                            <span>ID: {row['username']}</span>
                        </div>
                        <h3 style="color:#1e293b; margin:10px 0;">{row['content']}</h3>
                        {link_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # 点赞 (独立按钮防止 HTML 注入问题)
                    if st.button(f"👍 Like ({row['likes']})", key=f"lk_{i}"):
                        update_likes(i, row['likes'])
                        st.rerun()

    with tab2:
        st.info("管理员面板逻辑同上（略），确保你有权限修改 announcement。")


if __name__ == "__main__":
    main()
