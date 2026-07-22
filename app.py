import os
import uuid
import io
import streamlit as st
from PIL import Image

# 页面基本设置
st.set_page_config(page_title="临时图片压缩与分享", layout="centered")

# 创建本地临时存放目录
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# 1. 检查 URL 中是否有查询参数 (例如 ?id=xxxx)
query_params = st.query_params
file_id = query_params.get("id", None)

# =============================================================
# 场景 A：用户通过专属链接访问 (URL 包含 ?id=xxxx)
# =============================================================
if file_id:
    st.title("🖼️ 查看/下载图片")
    
    # 在本地查找对应的图片
    matched_files = [f for f in os.listdir(TEMP_DIR) if f.startswith(file_id)]
    
    if matched_files:
        target_filename = matched_files[0]
        file_path = os.path.join(TEMP_DIR, target_filename)
        
        # 显示图片预览
        st.image(file_path, caption=f"文件名: {target_filename}", use_container_width=True)
        
        # 读取文件流提供下载
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        st.download_button(
            label="⬇️ 一键下载此 JPEG 图片",
            data=file_bytes,
            file_name=target_filename,
            mime="image/jpeg",
            type="primary"
        )
        
        st.divider()
        if st.button("⬅️ 返回主页（我也要压缩图片）"):
            st.query_params.clear()
            st.rerun()
            
    else:
        st.error("❌ 该图片不存在或已被休眠机制抹除！")
        if st.button("返回首页"):
            st.query_params.clear()
            st.rerun()

# =============================================================
# 场景 B：普通访问 / 主页（上传、压缩、预览、分享）
# =============================================================
else:
    st.title("🗂️ 图片压缩 & 临时分享站")

    # 1. 文件上传/拖入区
    uploaded_file = st.file_uploader(
        "拖入或选择图片 (支持 PNG, JPG, JPEG, WEBP)", 
        type=["jpg", "jpeg", "png", "webp"]
    )

    if uploaded_file:
        # 获取原始文件大小 (KB)
        raw_bytes = uploaded_file.getvalue()
        original_size_kb = len(raw_bytes) / 1024

        st.subheader("1. 原始图片预览")
        # 打开原始图片
        orig_image = Image.open(io.BytesIO(raw_bytes))
        st.image(orig_image, caption=f"原图 ({uploaded_file.name}) - {original_size_kb:.1f} KB", use_container_width=True)

        st.divider()
        st.subheader("2. 压缩参数设置")

        # 布局：压缩质量控制条 + 强制 JPEG 提示
        col1, col2 = st.columns([2, 1])
        with col1:
            quality = st.slider("压缩质量 (Quality)", min_value=1, max_value=100, value=75, format="%d%%")
        with col2:
            st.selectbox("输出格式 (强制)", ["JPEG"], disabled=True)

        # 2. 内存中进行强制 JPEG 转换与压缩
        img_temp = orig_image.copy()
        # RGBA / P 模式转为 RGB 才能保存为 JPEG
        if img_temp.mode in ("RGBA", "P", "LA"):
            # 使用白色背景填充透明区域
            background = Image.new("RGB", img_temp.size, (255, 255, 255))
            if img_temp.mode == "RGBA":
                background.paste(img_temp, mask=img_temp.split()[3])
            else:
                background.paste(img_temp)
            img_temp = background
        elif img_temp.mode != "RGB":
            img_temp = img_temp.convert("RGB")

        # 导出到内存二进制流
        compressed_buffer = io.BytesIO()
        img_temp.save(compressed_buffer, format="JPEG", quality=quality, optimize=True)
        compressed_bytes = compressed_buffer.getvalue()
        compressed_size_kb = len(compressed_bytes) / 1024

        # 计算压缩率
        reduce_pct = ((original_size_kb - compressed_size_kb) / original_size_kb) * 100

        st.subheader("3. 压缩效果实时预览")
        st.image(compressed_bytes, caption=f"压缩后预览 - {compressed_size_kb:.1f} KB (体积变化: {reduce_pct:+.1f}%)", use_container_width=True)

        # 3. 下载与暂存功能 (修复下载不成功的关键：数据直接绑定内存字节流)
        st.subheader("4. 下载与生成分享链接")
        
        # 预设输出文件名 (强制 .jpg 扩展名)
        base_name = os.path.splitext(uploaded_file.name)[0]
        output_filename = f"{base_name}_compressed.jpg"

        dl_col, share_col = st.columns([1, 1])

        with dl_col:
            # 直接下载按钮 (无需保存到磁盘即可直接下)
            st.download_button(
                label="⬇️ 直接下载压缩图片",
                data=compressed_bytes,
                file_name=output_filename,
                mime="image/jpeg",
                type="primary",
                use_container_width=True
            )

        with share_col:
            # 存入本地磁盘并生成直链
            if st.button("🔗 暂存并生成分享链接", use_container_width=True):
                short_id = str(uuid.uuid4())[:6]
                saved_filename = f"{short_id}_{output_filename}"
                save_path = os.path.join(TEMP_DIR, saved_filename)

                # 写入本地文件
                with open(save_path, "wb") as f:
                    f.write(compressed_bytes)

                st.success("已暂存到云端！")
                st.info("将下方链接复制发送给其他人即可直接打开：")
                st.code(f"?id={short_id}", language="text")

    st.divider()

    # 底部：云端已暂存的文件列表
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
                if st.button("查看", key=f"view_{fname}"):
                    st.query_params["id"] = fid
                    st.rerun()
            with c3:
                with open(fpath, "rb") as f:
                    st.download_button("下载", f.read(), file_name=fname, mime="image/jpeg", key=f"dl_{fname}")
    else:
        st.caption("暂无暂存文件")
