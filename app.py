import os
import random
import io
import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

# 页面基础配置
st.set_page_config(page_title="极速本地图片批量压缩", layout="centered")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# -------------------------------------------------------------
# 🚀 自定义 CSS 样式（让按钮更大、更显眼、更好点）
# -------------------------------------------------------------
st.markdown("""
<style>
/* 放大并美化底部的下载按钮，提高手感 */
div[data-testid="stDownloadButton"] > button {
    width: 100%;
    min-height: 42px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 🚀 性能优化：高清压缩 + 适中尺寸缩略图 (280px，既清晰又极快)
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_and_compress_image(raw_bytes, quality):
    """内存中高速压缩高清原图"""
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
    return compressed_buf.getvalue(), img.width, img.height

@st.cache_data(show_spinner=False)
def generate_medium_thumbnail(raw_bytes, max_size=(280, 280)):
    """生成放大后的适中缩略图（约 10~15 KB），兼顾清晰度与加载速度"""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    # 动态缩放到最大 280px，看得清细节又不卡 CPU
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()

# 处理 URL 参数（链接查看逻辑）
query_params = st.query_params
file_id = query_params.get("id", None)

# =============================================================
# 场景 A：凭借专属链接查看/下载图片
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

        col_left, col_right = st.columns([1.2, 2])
        with col_left:
            # 适中预览图
            med_thumb = generate_medium_thumbnail(full_file_bytes, max_size=(320, 320))
            st.image(med_thumb, caption="清晰预览", use_container_width=True)
        with col_right:
            st.success(f"📄 **{display_name}**")
            st.caption(f"文件大小：{file_size_kb:.1f} KB")
            st.write("")
            
            # 秒级大按钮下载
            st.download_button(
                label=f"⬇️ 一键下载原图 ({file_size_kb:.1f} KB)",
                data=full_file_bytes,
                file_name=display_name,
                mime="image/jpeg",
                type="primary",
                use_container_width=True,
                key="dl_view_btn"
            )

        st.divider()
        st.markdown('<a href="/" target="_self" style="display:inline-block; padding:0.5rem 1rem; background-color:#F0F2F6; color:#333; text-decoration:none; border-radius:8px;">⬅️ 返回压缩主页</a>', unsafe_allow_html=True)
    else:
        st.error("❌ 该图片不存在或已被彻底清除！")
        st.markdown('<a href="/" target="_self" style="display:inline-block; padding:0.5rem 1rem; background-color:#F0F2F6; color:#333; text-decoration:none; border-radius:8px;">返回首页</a>', unsafe_allow_html=True)

# =============================================================
# 场景 B：主页面（放大版高清预览 + 100% 秒下载）
# =============================================================
else:
    st.markdown("<h2 style='text-align: center;'>⚡ 极速图片批量压缩工具</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>🔒 高清清晰预览 · 秒级打包暂存与下载</p>", unsafe_allow_html=True)

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
            images_to_process.append({"bytes": f.getvalue(), "name": f.name})

    if paste_result.image_data is not None:
        buf = io.BytesIO()
        paste_result.image_data.convert("RGB").save(buf, format="JPEG")
        images_to_process.append({"bytes": buf.getvalue(), "name": "pasted_img.jpg"})

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
            
            st.toast(f"处理完成！已暂存 {len(images_to_process)} 张图片", icon="✅")
            st.rerun()

        st.subheader(f"🖼️ 待处理列表")

        # 放大的预览排版（180px - 280px）
        for idx, item in enumerate(images_to_process):
            raw_bytes = item["bytes"]
            orig_size_kb = len(raw_bytes) / 1024
            
            compressed_bytes, img_w, img_h = process_and_compress_image(raw_bytes, quality)
            compressed_size_kb = len(compressed_bytes) / 1024
            reduce_pct = ((orig_size_kb - compressed_size_kb) / orig_size_kb) * 100
            
            med_bytes = generate_medium_thumbnail(raw_bytes)

            with st.container(border=True):
                p_col1, p_col2 = st.columns([1, 2.5])
                with p_col1:
                    st.image(med_bytes, use_container_width=True) # 撑满左侧一栏，放大且清晰
                with p_col2:
                    st.markdown(f"📄 **{item['name']}** (`{img_w}x{img_h}px`)")
                    st.markdown(f"原始体积：`{orig_size_kb:.1f} KB`")
                    st.markdown(f"预估压缩：**{compressed_size_kb:.1f} KB** (`{reduce_pct:+.1f}%`) ")

    st.divider()

    # 4. 底部暂存列表 & 一键删除区
    files = [f for f in os.listdir(TEMP_DIR) if os.path.isfile(os.path.join(TEMP_DIR, f))]
    
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.subheader("📁 云端已暂存的文件")
    with top_col2:
        if files:
            if st.button("🗑️ 清空暂存", type="secondary"):
                for fname in files:
                    file_path = os.path.join(TEMP_DIR, fname)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                st.toast("已清空！", icon="🧹")
                st.rerun()

    if files:
        for idx, fname in enumerate(files):
            fid = fname.split("_")[0]
            display_name = fname.split("_", 1)[1] if "_" in fname else fname
            fpath = os.path.join(TEMP_DIR, fname)
            fsize = os.path.getsize(fpath) / 1024
            
            with open(fpath, "rb") as f_item:
                f_bytes = f_item.read()

            med_b = generate_medium_thumbnail(f_bytes)

            c0, c1, c2, c3 = st.columns([1, 2, 1, 1.2])
            with c0:
                st.image(med_b, use_container_width=True) # 暂存列表中也进行了放大显示
            with c1:
                st.markdown(f"**{display_name}**")
                st.caption(f"体积: {fsize:.1f} KB")
            with c2:
                st.markdown(f'<a href="?id={fid}" target="_self" style="display:block; text-align:center; padding:0.5rem; background:#F0F2F6; color:#333; border-radius:8px; text-decoration:none; font-size:0.85rem; font-weight:500;">👁️ 查看</a>', unsafe_allow_html=True)
            with c3:
                st.download_button(
                    label="⬇️ 下载", 
                    data=f_bytes, 
                    file_name=display_name, 
                    mime="image/jpeg", 
                    type="primary",
                    key=f"med_dl_{idx}_{fid}"
                )
    else:
        st.caption("暂无文件，点击上方【一键压缩并暂存所有图片】即可生成。")
