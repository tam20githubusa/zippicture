import os
import random
import io
import threading
import http.server
import socketserver
import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

# 1. 页面基础配置
st.set_page_config(page_title="本地图片批量压缩工具", layout="centered")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# -------------------------------------------------------------
# 🌐 终极黑科技：在后台启动一个轻量 HTTP 静态文件下载服务器
# -------------------------------------------------------------
HTTP_PORT = 8502  # 静态文件服务端口

def start_static_server():
    """后台启动静态文件 HTTP 服务，专门负责稳定下载"""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=TEMP_DIR, **kwargs)
        def log_message(self, format, *args):
            pass # 禁用日志输出
            
    with socketserver.TCPServer(("", HTTP_PORT), Handler) as httpd:
        httpd.serve_forever()

# 确保线程只启动一次
if "server_started" not in st.session_state:
    try:
        t = threading.Thread(target=start_static_server, daemon=True)
        t.start()
        st.session_state["server_started"] = True
    except Exception:
        pass

@st.cache_data(show_spinner=False)
def process_and_compress_image(raw_bytes, quality):
    """内存中高速压缩图片"""
    img = Image.open(io.BytesIO(raw_bytes))
    
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            bg.paste(img, mask=img.split()[3])
        else:
            bg.paste(img)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    compressed_buf = io.BytesIO()
    img.save(compressed_buf, format="JPEG", quality=quality, optimize=True)
    compressed_bytes = compressed_buf.getvalue()
    
    return compressed_bytes, img.width, img.height

@st.cache_data(show_spinner=False)
def generate_preview_thumbnail(file_bytes, max_size=(1024, 1024)):
    """生成轻量级预览缩略图"""
    img = Image.open(io.BytesIO(file_bytes))
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

# 处理 URL 参数（链接查看逻辑）
query_params = st.query_params
file_id = query_params.get("id", None)

# =============================================================
# 场景 A：凭借专属链接查看图片
# =============================================================
if file_id:
    st.title("🖼️ 查看/下载图片")
    matched_files = [f for f in os.listdir(TEMP_DIR) if f.startswith(file_id)]
    
    if matched_files:
        target_filename = matched_files[0]
        file_path = os.path.join(TEMP_DIR, target_filename)
        display_name = target_filename.split("_", 1)[1] if "_" in target_filename else target_filename
        
        with open(file_path, "rb") as f:
            full_file_bytes = f.read()

        file_size_kb = len(full_file_bytes) / 1024

        # 原生直连下载按钮 (使用 100% 稳定的 download 属性)
        st.download_button(
            label=f"⬇️ 立即下载该 JPEG 图片 ({file_size_kb:.1f} KB)",
            data=full_file_bytes,
            file_name=display_name,
            mime="image/jpeg",
            type="primary",
            use_container_width=True,
            key="dl_view_btn"
        )
        st.write("")
        
        preview_bytes = generate_preview_thumbnail(full_file_bytes)
        st.image(preview_bytes, caption=f"预览图 - {display_name}", use_container_width=True)

        st.divider()
        st.markdown('<a href="/" target="_self" style="display:inline-block; padding:0.5rem 1rem; background-color:#F0F2F6; color:#333; text-decoration:none; border-radius:8px;">⬅️ 返回压缩主页</a>', unsafe_allow_html=True)
    else:
        st.error("❌ 该图片不存在或已被彻底清除！")
        st.markdown('<a href="/" target="_self" style="display:inline-block; padding:0.5rem 1rem; background-color:#F0F2F6; color:#333; text-decoration:none; border-radius:8px;">返回首页</a>', unsafe_allow_html=True)

# =============================================================
# 场景 B：主页面（支持批量压缩与 100% 稳定下载）
# =============================================================
else:
    st.markdown("<h2 style='text-align: center;'>本地图片批量压缩工具</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>🔒 云端极速内存渲染 · 支持一键批量处理</p>", unsafe_allow_html=True)

    # 1. 控制卡片区
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            quality = st.slider("压缩质量", min_value=1, max_value=100, value=75, format="%d%%")
        with col2:
            st.selectbox("输出格式", ["JPEG"], disabled=True)

    # 2. 上传与粘贴栏
    uploaded_files = st.file_uploader(
        "点击选择或将图片拖拽到这里（支持多选）", 
        type=["jpg", "jpeg", "png", "webp"], 
        accept_multiple_files=True
    )

    paste_col1, paste_col2 = st.columns([1.5, 3.5])
    with paste_col1:
        paste_result = paste_image_button("📋 粘贴剪贴板图片", key="paste_btn")
    
    images_to_process = []

    if uploaded_files:
        for f in uploaded_files:
            images_to_process.append({"bytes": f.getvalue()})

    if paste_result.image_data is not None:
        buf = io.BytesIO()
        paste_result.image_data.convert("RGB").save(buf, format="JPEG")
        images_to_process.append({"bytes": buf.getvalue()})

    # 3. 待处理列表 & ⚡ 批量压缩大按键
    if images_to_process:
        st.divider()
        
        if st.button(f"⚡ 一键压缩并暂存所有图片 ({len(images_to_process)}张)", type="primary", use_container_width=True):
            for idx, item in enumerate(images_to_process):
                raw_bytes = item["bytes"]
                compressed_bytes, _, _ = process_and_compress_image(raw_bytes, quality)
                
                rand_num = f"{random.randint(0, 9999):04d}"
                out_filename = f"IMG_{rand_num}.jpg"
                save_filename = f"{rand_num}_{out_filename}"
                save_path = os.path.join(TEMP_DIR, save_filename)
                
                with open(save_path, "wb") as f_out:
                    f_out.write(compressed_bytes)
            
            st.toast(f"成功处理并暂存了 {len(images_to_process)} 张图片！", icon="✅")
            st.rerun()

        st.subheader(f"🖼️ 待处理列表")

        for idx, item in enumerate(images_to_process):
            with st.container(border=True):
                raw_bytes = item["bytes"]
                orig_size_kb = len(raw_bytes) / 1024
                
                compressed_bytes, img_w, img_h = process_and_compress_image(raw_bytes, quality)
                compressed_size_kb = len(compressed_bytes) / 1024
                reduce_pct = ((orig_size_kb - compressed_size_kb) / orig_size_kb) * 100

                p_col1, p_col2 = st.columns([1, 2])
                with p_col1:
                    st.image(compressed_bytes, use_container_width=True)
                
                with p_col2:
                    st.caption(f"尺寸：{img_w} x {img_h} px")
                    st.markdown(f"**体积预估**：{orig_size_kb:.1f} KB ➔ **{compressed_size_kb:.1f} KB** "
                                f"(`{reduce_pct:+.1f}%`) ")

    st.divider()

    # 4. 底部暂存列表 & 一键删除区
    files = [f for f in os.listdir(TEMP_DIR) if os.path.isfile(os.path.join(TEMP_DIR, f))]
    
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.subheader("📁 云端已暂存的临时文件")
    with top_col2:
        if files:
            if st.button("🗑️ 清空所有暂存", type="secondary"):
                for fname in files:
                    file_path = os.path.join(TEMP_DIR, fname)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                st.toast("已清空所有暂存图片！", icon="🧹")
                st.rerun()

    if files:
        for idx, fname in enumerate(files):
            fid = fname.split("_")[0]
            display_name = fname.split("_", 1)[1] if "_" in fname else fname
            fpath = os.path.join(TEMP_DIR, fname)
            fsize = os.path.getsize(fpath) / 1024
            
            c1, c2, c3 = st.columns([2.5, 1.2, 1.2])
            with c1:
                st.text(f"📄 {display_name} ({fsize:.1f} KB)")
            with c2:
                # 网页原生跳转，绝对能打开
                st.markdown(f'<a href="?id={fid}" target="_self" style="display:block; text-align:center; padding:0.375rem; background:#F0F2F6; color:#333; border-radius:8px; text-decoration:none;">👁️ 查看/直链</a>', unsafe_allow_html=True)
            with c3:
                # 读取二进制并直接绑定到 Streamlit 最原生的下载器上（带独一无二的 index key）
                with open(fpath, "rb") as f_item:
                    f_bytes = f_item.read()
                st.download_button(
                    label="⬇️ 下载", 
                    data=f_bytes, 
                    file_name=display_name, 
                    mime="image/jpeg", 
                    key=f"stable_dl_{idx}_{fid}"
                )
    else:
        st.caption("暂无暂存文件，点击上方【⚡ 一键压缩并暂存所有图片】后会出现在这里。")
