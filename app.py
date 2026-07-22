import os
import uuid
import streamlit as st
from PIL import Image

# 设置页面属性
st.set_page_config(page_title="临时图片分享站", layout="centered")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# 1. 检查 URL 中是否有查询参数 (例如 ?id=xxxx)
query_params = st.query_params
file_id = query_params.get("id", None)

# -------------------------------------------------------------
# 场景 A：用户通过直链访问 (URL 带着 ?id=xxxx)
# -------------------------------------------------------------
if file_id:
    st.title("🖼️ 查看/下载图片")
    
    # 在本地查找包含该 file_id 的图片
    matched_files = [f for f in os.listdir(TEMP_DIR) if f.startswith(file_id)]
    
    if matched_files:
        target_filename = matched_files[0]
        file_path = os.path.join(TEMP_DIR, target_filename)
        
        # 显示图片预览
        st.image(file_path, caption=target_filename, use_container_width=True)
        
        # 提供一键下载
        with open(file_path, "rb") as f:
            st.download_button(
                label="⬇️ 下载这张图片",
                data=f.read(),
                file_name=target_filename,
                mime="image/jpeg",
                type="primary"
            )
        
        st.divider()
        if st.button("⬅️ 我也要上传/压缩图片"):
            # 清空 URL 参数返回首页
            st.query_params.clear()
            st.rerun()
            
    else:
        st.error("❌ 该图片不存在或已因应用休眠而被清除！")
        if st.button("返回首页"):
            st.query_params.clear()
            st.rerun()

# -------------------------------------------------------------
# 场景 B：普通访问 (主页 - 上传压缩)
# -------------------------------------------------------------
else:
    st.title("🗂️ 极简临时图片压缩与分享")
    
    uploaded_file = st.file_uploader("上传图片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        quality = st.slider("压缩质量 (Quality)", 10, 90, 70)
        
        if st.button("压缩并生成分享链接"):
            image = Image.open(uploaded_file)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            # 生成 6 位随机短 ID
            short_id = str(uuid.uuid4())[:6]
            filename = f"{short_id}_{uploaded_file.name}"
            save_path = os.path.join(TEMP_DIR, filename)
            
            # 保存到本地
            image.save(save_path, format="JPEG", quality=quality, optimize=True)
            
            st.success("压缩成功！")
            
            # 显示专属查看链接
            # 自动获取当前应用的主域名 (包含路径)
            share_url = f"?id={short_id}"
            
            st.subheader("🔗 你的专属分享链接：")
            st.info("将下方链接复制发送给其他人即可直接打开图片：")
            
            # 在 Streamlit 中提供可一键复制的代码块呈现链接
            st.code(share_url, language="text")
            
            # 预览按钮：直接跳转查看
            if st.button("👁️ 立即通过链接查看效果"):
                st.query_params["id"] = short_id
                st.rerun()

    st.divider()
    
    # 底部展示已暂存的文件
    st.subheader("📁 云端已有的临时文件")
    files = os.listdir(TEMP_DIR)
    if files:
        for fname in files:
            # 提取文件前 6 位 ID
            fid = fname.split("_")[0]
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"📄 {fname}")
            with col2:
                if st.button("查看/链接", key=fname):
                    st.query_params["id"] = fid
                    st.rerun()
    else:
        st.caption("暂无文件，上传后会自动呈现在这里。")
