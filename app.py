import os
import random
import io
import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

# 页面基础配置
st.set_page_config(page_title="本地图片批量压缩工具", layout="centered")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# -------------------------------------------------------------
# 🚀 性能优化：使用内存缓存加速图片解析与预览生成
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_and_compress_image(raw_bytes, quality):
    """在内存中快速压缩图片，避免频繁磁盘 I/O"""
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
    """专为场景 A 打造：生成小体积预览图，解决一行行极慢加载的问题"""
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
# 场景 A：凭借专属链接查看图片 (极速加载 + 正常下载)
# =============================================================
if file_id:
    st.title("🖼️ 查看/下载图片")
    matched_files = [f for f in os.listdir(TEMP_DIR) if f.startswith(file_id)]
    
    if matched_files:
        target_filename = matched_files[0]
        file_path = os.path.join(TEMP_DIR, target_filename)
        display_name = target_filename.split("_", 1)[1] if "_" in target_filename else target_filename
        
        # 1. 一次性读取完整高清二进制数据（用于下载）
        with open(file_path, "rb") as f:
            full_file_bytes = f.read()

        file_size_kb = len(full_file_bytes) / 1024

        # 2. 优先放置下载按钮（确保下载体验流畅，不用等大图加载完毕）
        st.download_button(
            label=f"⬇️ 立即下载该 JPEG 图片 ({file_size_kb:.1f} KB)",
            data=full_file_bytes,
            file_name=display_name,
            mime="image/jpeg",
            type="primary",
            use_container_width=True,
            key="view_page_download_btn"
        )
        
        # 3. 内存生成轻量级缩略图渲染，防止网页崩溃或一行行极慢加载
        preview_bytes = generate_preview_thumbnail(full_file_bytes)
        st.image(preview_bytes, caption=f"预览图 - {display_name}", use_container_width=True)

        st.divider()
        if st.button("⬅️ 返回压缩主页"):
            st.query_params.clear()
            st.rerun()
    else:
        st.error("❌ 该图片不存在或已被彻底清除！")
        if st.button("返回首页"):
            st.query_params.clear()
            st.rerun()

# =============================================================
# 场景 B：主页面（压缩、批量处理、内存优化版）
# =============================================================
else:
    st.markdown("<h2 style='text-align: center;'>本地图片批量压缩工具</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>🔒 云端极速内存渲染 · 拖动滑块无延迟预览</p>", unsafe_allow_html=True)

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

    # 3. 极速预览区
    if images_to_process:
        st.divider()
        st.subheader(f"🖼️ 待处理图片列表 ({len(images_to_process)}张)")

        for idx, item in enumerate(images_to_process):
            with st.container(border=True):
                raw_bytes = item["bytes"]
                orig_size_kb = len(raw_bytes) / 1024
                
                compressed_bytes, img_w, img_h = process_and_compress_image(raw_bytes, quality)
                compressed_size_kb = len(compressed_bytes) / 1024
                
                reduce_pct = ((orig_size_kb - compressed_size_kb) / orig_size_kb) * 100

                rand_num = f"{random.randint(0, 9999):04d}"
                out_filename = f"IMG_{rand_num}.jpg"

                p_col1, p_col2 = st.columns([1, 2])
                with p_col1:
                    st.image(compressed_bytes, use_container_width=True)
                
                with p_col2:
                    st.markdown(f"**预设文件名**：`{out_filename}`")
                    st.caption(f"尺寸：{img_w} x {img_h} px")
                    st.markdown(f"**体积变动**：{orig_size_kb:.1f} KB ➔ **{compressed_size_kb:.1f} KB** "
                                f"(`{reduce_pct:+.1f}%`) ")

                    btn_c1, btn_c2 = st.columns(2)

                    with btn_c1:
                        st.download_button(
                            label="⬇️ 下载 JPEG",
                            data=compressed_bytes,
                            file_name=out_filename,
                            mime="image/jpeg",
                            type="primary",
                            key=f"dl_{idx}_{rand_num}"
                        )
                    with btn_c2:
                        if st.button("🔗 生成分享链接", key=f"share_{idx}_{rand_num}"):
                            save_filename = f"{rand_num}_{out_filename}"
                            save_path = os.path.join(TEMP_DIR, save_filename)
                            with open(save_path, "wb") as f_out:
                                f_out.write(compressed_bytes)
                            st.success("已生成直链！")
                            st.code(f"?id={rand_num}", language="text")

    st.divider()

    # 4. 底部暂存列表 & 一键删除区
    files = os.listdir(TEMP_DIR)
    
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
        for fname in files:
            fid = fname.split("_")[0]
            display_name = fname.split("_", 1)[1] if "_" in fname else fname
            fpath = os.path.join(TEMP_DIR, fname)
            fsize = os.path.getsize(fpath) / 1024
            
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.text(f"📄 {display_name} ({fsize:.1f} KB)")
            with c2:
                if st.button("查看", key=f"v_{fname}"):
                    st.query_params["id"] = fid
                    st.rerun()
            with c3:
                with open(fpath, "rb") as f_item:
                    st.download_button(
                        "下载", 
                        f_item.read(), 
                        file_name=display_name, 
                        mime="image/jpeg", 
                        key=f"d_{fname}"
                    )
    else:
        st.caption("暂无暂存文件")
