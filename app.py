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
        
        # 显示直链图片
        display_name = target_filename.split("_", 1)[1] if "_" in target_filename else target_filename
        st.image(file_path, caption=f"文件名: {display_name}", width="stretch")
        
        with open(file_path, "rb") as f:
            st.download_button(
                label="⬇️ 下载这张图片",
                data=f.read(),
                file_name=display_name,
                mime="image/jpeg",
                type="primary"
            )
        st.divider()
        if st.button("⬅️ 我也要压缩图片"):
            st.query_params.clear()
            st.rerun()
    else:
        st.error("❌ 该图片不存在或已被彻底清除！")
        if st.button("返回首页"):
            st.query_params.clear()
            st.rerun()

# =============================================================
# 场景 B：主页面（压缩、批量处理、自动暂存、一键删除）
# =============================================================
else:
    st.markdown("<h2 style='text-align: center;'>本地图片批量压缩工具</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>🔒 云端临时环境运行 · 拖动滑块实时无感测算大小</p>", unsafe_allow_html=True)

    # 1. 控制卡片区（双列布局：压缩质量 + 强制输出格式）
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
    
    # 整合上传与粘贴图片
    images_to_process = []

    if uploaded_files:
        for f in uploaded_files:
            images_to_process.append({"bytes": f.getvalue()})

    if paste_result.image_data is not None:
        buf = io.BytesIO()
        paste_result.image_data.convert("RGB").save(buf, format="JPEG")
        images_to_process.append({"bytes": buf.getvalue()})

    # 3. 压缩与预览区（自动写盘存入云端）
    if images_to_process:
        st.divider()
        st.subheader(f"🖼️ 待处理图片列表 ({len(images_to_process)}张)")

        for idx, item in enumerate(images_to_process):
            with st.container(border=True):
                raw_bytes = item["bytes"]
                orig_size_kb = len(raw_bytes) / 1024
                
                img = Image.open(io.BytesIO(raw_bytes))
                
                # 转换色彩模式为 RGB (透明背景填充白色)
                if img.mode in ("RGBA", "P", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    else:
                        bg.paste(img)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # 内存压缩
                compressed_buf = io.BytesIO()
                img.save(compressed_buf, format="JPEG", quality=quality, optimize=True)
                compressed_bytes = compressed_buf.getvalue()
                compressed_size_kb = len(compressed_bytes) / 1024
                
                reduce_pct = ((orig_size_kb - compressed_size_kb) / orig_size_kb) * 100

                # 生成 4 位随机数字文件名
                rand_num = f"{random.randint(0, 9999):04d}"
                out_filename = f"IMG_{rand_num}.jpg"

                # 自动暂存入本地云端目录
                save_filename = f"{rand_num}_{out_filename}"
                save_path = os.path.join(TEMP_DIR, save_filename)
                with open(save_path, "wb") as f_out:
                    f_out.write(compressed_bytes)

                # 展示与操作
                p_col1, p_col2 = st.columns([1, 2])
                with p_col1:
                    st.image(compressed_bytes, width="stretch")
                
                with p_col2:
                    st.markdown(f"**预设文件名**：`{out_filename}`")
                    st.caption(f"尺寸：{img.width} x {img.height} px")
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
                        st.caption("🔗 分享后缀：")
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
                    st.download_button("下载", f_item.read(), file_name=display_name, mime="image/jpeg", key=f"d_{fname}")
    else:
        st.caption("暂无暂存文件")
