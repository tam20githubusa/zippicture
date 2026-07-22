import os
import uuid
import io
import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

# 页面基础配置
st.set_page_config(page_title="本地图片批量压缩工具", layout="centered")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

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
        
        # 兼容最新 Streamlit width 语法
        st.image(file_path, caption=f"文件名: {target_filename}", width="stretch")
        
        with open(file_path, "rb") as f:
            st.download_button(
                label="⬇️ 下载这张图片",
                data=f.read(),
                file_name=target_filename,
                mime="image/jpeg",
                type="primary"
            )
        st.divider()
        if st.button("⬅️ 我也要压缩图片"):
            st.query_params.clear()
            st.rerun()
    else:
        st.error("❌ 该图片不存在或已被休眠机制抹除！")
        if st.button("返回首页"):
            st.query_params.clear()
            st.rerun()

# =============================================================
# 场景 B：主页面（卡片布局 + 粘贴导入 + 批量处理）
# =============================================================
else:
    # 顶部标题与副标题
    st.markdown("<h2 style='text-align: center;'>本地图片批量压缩工具</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>🔒 纯浏览器/云端临时环境运行 · 拖动滑块实时无感测算大小</p>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 控制卡片区（模拟截图中的三列控制栏）
    # ---------------------------------------------------------
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1.2, 1.2])
        
        with col1:
            quality = st.slider("压缩质量", min_value=1, max_value=100, value=75, format="%d%%")
        with col2:
            st.selectbox("输出格式", ["JPEG"], disabled=True)
        with col3:
            max_width = st.number_input("限制最大宽度 (0为不缩放)", min_value=0, max_value=8000, value=0, step=100)

    # ---------------------------------------------------------
    # 上传与粘贴栏
    # ---------------------------------------------------------
    uploaded_files = st.file_uploader(
        "点击选择或将图片拖拽到这里（支持多选）", 
        type=["jpg", "jpeg", "png", "webp"], 
        accept_multiple_files=True
    )

    paste_col1, paste_col2 = st.columns([1.5, 3.5])
    with paste_col1:
        paste_result = paste_image_button("📋 粘贴剪贴板图片", key="paste_btn")
    
    # ---------------------------------------------------------
    # 统一处理图片列表 (整合上传与粘贴)
    # ---------------------------------------------------------
    images_to_process = []

    if uploaded_files:
        for f in uploaded_files:
            images_to_process.append({"name": f.name, "bytes": f.getvalue()})

    if paste_result.image_data is not None:
        buf = io.BytesIO()
        paste_result.image_data.convert("RGB").save(buf, format="JPEG")
        images_to_process.append({"name": "pasted_image.jpg", "bytes": buf.getvalue()})

    # ---------------------------------------------------------
    # 压缩与预览展示区
    # ---------------------------------------------------------
    if images_to_process:
        st.divider()
        st.subheader(f"🖼️ 待处理图片列表 ({len(images_to_process)}张)")

        for idx, item in enumerate(images_to_process):
            with st.container(border=True):
                raw_bytes = item["bytes"]
                orig_size_kb = len(raw_bytes) / 1024
                
                img = Image.open(io.BytesIO(raw_bytes))
                
                # 最大宽度缩放
                if max_width > 0 and img.width > max_width:
                    w_percent = (max_width / float(img.width))
                    h_size = int((float(img.height) * float(w_percent)))
                    img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                
                # 强制转换 RGB
                if img.mode in ("RGBA", "P", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    else:
                        bg.paste(img)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # 压缩到 JPEG 字节流
                compressed_buf = io.BytesIO()
                img.save(compressed_buf, format="JPEG", quality=quality, optimize=True)
                compressed_bytes = compressed_buf.getvalue()
                compressed_size_kb = len(compressed_bytes) / 1024
                
                reduce_pct = ((orig_size_kb - compressed_size_kb) / orig_size_kb) * 100

                p_col1, p_col2 = st.columns([1, 2])
                with p_col1:
                    st.image(compressed_bytes, width="stretch")
                
                with p_col2:
                    st.markdown(f"**文件名**：`{item['name']}`")
                    st.caption(f"尺寸：{img.width} x {img.height} px")
                    st.markdown(f"**体积变动**：{orig_size_kb:.1f} KB ➔ **{compressed_size_kb:.1f} KB** "
                                f"(`{reduce_pct:+.1f}%`) ")

                    btn_c1, btn_c2 = st.columns(2)
                    base_name = os.path.splitext(item['name'])[0]
                    out_filename = f"{base_name}_compressed.jpg"

                    with btn_c1:
                        st.download_button(
                            label="⬇️ 下载 JPEG",
                            data=compressed_bytes,
                            file_name=out_filename,
                            mime="image/jpeg",
                            type="primary",
                            key=f"dl_{idx}_{item['name']}"
                        )
                    with btn_c2:
                        if st.button("🔗 生成分享链接", key=f"share_{idx}_{item['name']}"):
                            short_id = str(uuid.uuid4())[:6]
                            save_filename = f"{short_id}_{out_filename}"
                            save_path = os.path.join(TEMP_DIR, save_filename)

                            with open(save_path, "wb") as f_out:
                                f_out.write(compressed_bytes)

                            st.success("已生成云端临时链接！")
                            st.code(f"?id={short_id}", language="text")

    st.divider()

    # 底部暂存列表
    st.subheader("📁 云端已暂存的临时文件")
    files = os.listdir(TEMP_DIR)
    if files:
        for fname in files:
            fid = fname.split("_")[0]
            fpath = os.path.join(TEMP_DIR, fname)
            fsize = os.path.getsize(fpath) / 1024
            
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.text(f"📄 {fname} ({fsize:.1f} KB)")
            with c2:
                if st.button("查看", key=f"v_{fname}"):
                    st.query_params["id"] = fid
                    st.rerun()
            with c3:
                with open(fpath, "rb") as f_item:
                    st.download_button("下载", f_item.read(), file_name=fname, mime="image/jpeg", key=f"d_{fname}")
    else:
        st.caption("暂无暂存文件")
