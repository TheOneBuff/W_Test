import os

# [核心配置] 强制关闭 ChromaDB 的遥测功能，防止 capture() 报错
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import pandas as pd
import logging
import warnings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# 引入原生 Ollama 支持
from langchain_community.embeddings import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# 过滤掉 langchain_openai 的过时警告
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_openai")

# 向量库存储路径
CHROMA_PATH = "/app/chroma_db"


class RagService:
    def __init__(self, api_key: str, base_url: str = None, model_name: str = None):
        """
        初始化 RAG 服务 (自动适配 Ollama 或 OpenAI)
        """
        self.model_name = model_name or "nomic-embed-text"
        self.api_key = api_key or "ollama"
        self.base_url = base_url or "http://host.docker.internal:11434/v1"

        logging.info(f"🔌 正在初始化 Embedding 模型: {self.model_name}")

        # 判断是否为 Ollama 环境
        is_ollama = "11434" in self.base_url or self.api_key == "ollama" or "localhost" in self.base_url

        if is_ollama:
            logging.info("🚀 检测到 Ollama 环境，已切换至原生 OllamaEmbeddings 模式...")
            # Ollama 原生接口 URL 不需要 /v1 后缀
            clean_base_url = self.base_url.replace("/v1", "").rstrip("/")

            self.embeddings = OllamaEmbeddings(
                base_url=clean_base_url,
                model=self.model_name
            )
        else:
            logging.info("🌍 正在使用标准 OpenAIEmbeddings 模式...")
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                model=self.model_name,
                # 兼容性设置：不检查上下文长度，防止报错
                chunk_size=10
            )

        self.vector_db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=self.embeddings
        )

    def delete_doc_by_source(self, file_path: str):
        """清除旧向量数据"""
        try:
            try:
                existing_data = self.vector_db.get(where={"source": file_path})
            except Exception:
                return  # 集合可能还没创建，直接返回

            if existing_data and existing_data['ids']:
                ids_to_delete = existing_data['ids']
                logging.info(f"🗑️ 正在清除旧数据: {file_path} (共 {len(ids_to_delete)} 条)")
                self.vector_db.delete(ids=ids_to_delete)
        except Exception as e:
            logging.warning(f"⚠️ 清理旧数据时遇到非致命警告: {e}")

    def process_document(self, file_path: str):
        """解析文件并存入向量库"""

        # 1. 先清理旧数据
        self.delete_doc_by_source(file_path)

        docs = []
        logging.info(f"📂 开始解析文件: {file_path}")

        try:
            if file_path.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
                docs = loader.load()
            elif file_path.endswith(".docx"):
                loader = Docx2txtLoader(file_path)
                docs = loader.load()
            elif file_path.endswith((".xlsx", ".xls", ".csv")):
                docs = self._parse_spreadsheet(file_path)
            else:
                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
        except Exception as e:
            logging.error(f"❌ 文件加载失败: {e}")
            raise e

        if not docs:
            logging.warning(f"⚠️ 文件中未提取到有效数据，跳过: {file_path}")
            return 0

        # 2. 文本切片
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )
        chunks = text_splitter.split_documents(docs)

        if not chunks:
            return 0

        # 3. 数据清洗
        valid_chunks = []
        for i, chunk in enumerate(chunks):
            content = str(chunk.page_content).strip()
            if not content: continue

            chunk.page_content = content

            # Metadata 清洗
            clean_meta = {"source": str(file_path), "chunk_index": int(i)}
            for k, v in chunk.metadata.items():
                if k not in clean_meta:
                    clean_meta[k] = str(v)

            chunk.metadata = clean_meta
            valid_chunks.append(chunk)

        if not valid_chunks:
            return 0

        logging.info(f"🚀 正在向 Embedding 模型 ({self.model_name}) 发送 {len(valid_chunks)} 条数据切片...")

        # 4. 存入数据库
        try:
            # 每次只发 50 条，防止本地 Ollama 压力过大
            batch_size = 50
            for i in range(0, len(valid_chunks), batch_size):
                batch = valid_chunks[i: i + batch_size]
                self.vector_db.add_documents(batch)
                logging.info(f"   ... 已处理批次 {i} 到 {i + len(batch)}")

        except Exception as e:
            logging.error(f"❌ Embedding API 调用失败: {e}")
            raise e

        logging.info(f"✅ 成功入库: {len(valid_chunks)} 条切片。")
        return len(valid_chunks)

    def _parse_spreadsheet(self, file_path: str):
        """解析表格"""
        df = None
        file_name = os.path.basename(file_path).lower()

        # CSV处理
        if file_path.endswith(".csv"):
            if "bug list" in file_name or "statistics" in file_name:
                logging.info(f"⏭️ 跳过非测试用例 CSV 文件: {file_name}")
                return []
            try:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python')
                except:
                    df = pd.read_csv(file_path, encoding='gbk', sep=None, engine='python')
            except Exception:
                return []
        # Excel处理
        else:
            try:
                xl = pd.ExcelFile(file_path)
                target_sheet = None
                for sheet in xl.sheet_names:
                    s_lower = sheet.lower()
                    if "test case" in s_lower or "testcase" in s_lower or "测试用例" in s_lower:
                        target_sheet = sheet
                        break

                if target_sheet:
                    df = pd.read_excel(file_path, sheet_name=target_sheet)
                else:
                    df = pd.read_excel(file_path, sheet_name=0)
            except Exception:
                return []

        if df is None or df.empty:
            return []

        # 列名清洗
        df.columns = df.columns.astype(str).str.strip()
        col_map = {c.lower(): c for c in df.columns}

        # 内容清洗
        df = df.astype(str).replace(["nan", "None", "NaN", "<NA>"], "")

        documents = []
        for index, row in df.iterrows():
            def get_val(keywords):
                for k in keywords:
                    k_lower = k.lower()
                    if k_lower in col_map:
                        val = row[col_map[k_lower]]
                        if val and val.strip(): return val.strip()
                    for clean_col in col_map.keys():
                        if k_lower in clean_col:
                            val = row[col_map[clean_col]]
                            if val and val.strip(): return val.strip()
                return ""

            title = get_val(['Purpose', 'Test Case', 'Test Name', '用例名称', '标题'])
            steps = get_val(['Steps Description', 'Steps', '测试步骤', '操作步骤'])
            mod = get_val(['Module', '模块'])
            nav1 = get_val(['first-class navigation', '一级导航'])
            nav2 = get_val(['second-class navigation', '二级导航'])
            full_module = f"{mod}/{nav1}/{nav2}".strip('/').replace('//', '/')
            pre = get_val(['Pre-Conditions', 'Pre-condition', '前置条件']) or '无'
            expected = get_val(['Expected Result', 'Expected', '预期结果'])

            if not title: continue

            content = f"模块:{full_module}\n标题:{title}\n前置:{pre}\n步骤:{steps}\n预期:{expected}"
            documents.append(Document(page_content=content, metadata={"row": int(index)}))

        return documents

    def search(self, query: str, k=4):
        return self.vector_db.similarity_search(query, k=k)