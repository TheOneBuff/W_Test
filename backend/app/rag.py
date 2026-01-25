import os

# [核心配置] 强制关闭 ChromaDB 的遥测功能，防止 capture() 报错
# 必须放在所有 import 之前
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import pandas as pd
import logging
import warnings
import requests  # 必须引入 requests
from typing import List

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# 引入原生 Ollama 支持
from langchain_community.embeddings import OllamaEmbeddings
# 保留引用以防万一，但主要逻辑使用下面的自定义类
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.schema.embeddings import Embeddings

# 过滤警告
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_openai")

# 向量库存储路径 (确保与 Docker 挂载的 /data 目录一致)
CHROMA_PATH = "/data/chroma_db"


# ----------------------------------------------------------------
# [核心修复] 自定义极简 Embedding 类
# 彻底解决 "input field must be a string" 和 "unexpected keyword" 兼容性问题
# ----------------------------------------------------------------
class SimpleOpenAIEmbeddings(Embeddings):
    """
    一个不依赖 langchain-openai 的极简客户端，
    直接通过 HTTP 请求调用 OpenAI 兼容接口 (如 LM Studio / vLLM)。
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 构造标准的 OpenAI 格式请求
        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        # LM Studio 等本地服务完美支持这种简单的 input 列表
        payload = {
            "input": texts,
            "model": self.model
        }

        try:
            # 设置 60秒超时
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                raise ValueError(f"Embedding API Error ({response.status_code}): {response.text}")

            data = response.json()
            if "data" not in data:
                raise ValueError(f"Unexpected API response format: {data}")

            # 确保按 index 排序返回，保证向量与文本一一对应
            sorted_data = sorted(data['data'], key=lambda x: x['index'])
            return [item['embedding'] for item in sorted_data]

        except Exception as e:
            logging.error(f"SimpleOpenAIEmbeddings Error: {str(e)}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# ----------------------------------------------------------------
# RAG 服务类
# ----------------------------------------------------------------
class RagService:
    def __init__(self, api_key: str, base_url: str = None, model_name: str = None):
        """
        初始化 RAG 服务
        """
        self.model_name = model_name or "nomic-embed-text"
        self.api_key = api_key or "ollama"
        self.base_url = base_url or "http://host.docker.internal:11434/v1"

        logging.info(f"🔌 正在初始化 Embedding 模型: {self.model_name}")

        # 判断是否为 Ollama 环境
        is_ollama = "11434" in self.base_url or self.api_key == "ollama" or "localhost" in self.base_url

        if is_ollama:
            logging.info("🚀 检测到 Ollama 环境，已切换至原生 OllamaEmbeddings 模式...")
            clean_base_url = self.base_url.replace("/v1", "").rstrip("/")
            self.embeddings = OllamaEmbeddings(
                base_url=clean_base_url,
                model=self.model_name
            )
        else:
            logging.info("🌍 使用 SimpleOpenAIEmbeddings (自定义兼容模式)...")
            # [核心修改] 使用自定义类，完全绕过 langchain-openai 的复杂逻辑
            self.embeddings = SimpleOpenAIEmbeddings(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model_name
            )

        self.vector_db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=self.embeddings
        )

    def delete_doc_by_source(self, file_path: str):
        """
        清除旧向量数据 (终极修复版 - 修复 limit 限制)
        """
        try:
            target_filename = os.path.basename(file_path)
            logging.info(f"🔍 [Delete] 正在全量扫描向量库，寻找文件名 '{target_filename}' ...")

            # [核心修复] limit=100000
            # 不加这个参数，Chroma 默认只返回前 100 条数据，导致永远删不掉后面的数据！
            all_data = self.vector_db.get(include=['metadatas'], limit=100000)

            if not all_data or not all_data['ids']:
                logging.warning("⚠️ [Delete] 向量库为空，无需操作。")
                return

            ids_to_delete = []
            scanned_count = len(all_data['ids'])
            logging.info(f"📊 [Delete] 当前库中总数据量: {scanned_count} 条")
            print(f"📊 [Delete] 当前库中总数据量: {scanned_count} 条")

            # 遍历查找
            for i, meta in enumerate(all_data['metadatas']):
                # 防御性编程：如果 meta 是 None (脏数据)，跳过
                if not meta:
                    continue

                source_path = meta.get('source', '')

                # 只要文件名匹配就删除
                if source_path.endswith(target_filename):
                    ids_to_delete.append(all_data['ids'][i])

            # 执行删除
            if ids_to_delete:
                count = len(ids_to_delete)
                logging.info(f"🎯 [Delete] 命中 {count} 条数据，准备物理删除...")
                print(f"🎯 [Delete] 命中 {count} 条数据，准备物理删除...")
                # 分批删除 (Chroma 对单次删除数量有限制)
                batch_size = 500
                for i in range(0, count, batch_size):
                    batch = ids_to_delete[i: i + batch_size]
                    self.vector_db.delete(ids=batch)

                logging.info(f"✅ [Delete] 成功清理 {count} 条向量数据。")
                print(f"✅ [Delete] 成功清理 {count} 条向量数据。")

            else:
                logging.warning(
                    f"⚠️ [Delete] 扫描了 {scanned_count} 条数据，未找到文件名匹配 '{target_filename}' 的记录。")

                # [调试] 打印前3条数据的路径，看看长什么样
                if scanned_count > 0:
                    sample = [m.get('source') for m in all_data['metadatas'][:3] if m]
                    logging.info(f"👀 [Debug] 库中数据路径示例: {sample}")

        except Exception as e:
            logging.error(f"❌ [Delete] 删除逻辑出错: {e}", exc_info=True)

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
            # 每次只发 20 条，防止本地服务压力过大
            batch_size = 20
            for i in range(0, len(valid_chunks), batch_size):
                batch = valid_chunks[i: i + batch_size]
                try:
                    self.vector_db.add_documents(batch)
                    logging.info(f"   ... 已处理批次 {i} 到 {i + len(batch)}")
                except Exception as e:
                    logging.error(f"❌ 批次插入失败 (Index {i}): {e}")
                    raise e

        except Exception as e:
            logging.error(f"❌ Embedding API 调用失败: {e}")
            raise e

        logging.info(f"✅ 成功入库: {len(valid_chunks)} 条切片。")
        return len(valid_chunks)

    def _parse_spreadsheet(self, file_path: str):
        """解析表格 (增强容错版)"""
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
                # 显式指定 engine='openpyxl'
                xl = pd.ExcelFile(file_path, engine='openpyxl')
                target_sheet = None
                for sheet in xl.sheet_names:
                    s_lower = sheet.lower()
                    if "test case" in s_lower or "testcase" in s_lower or "测试用例" in s_lower:
                        target_sheet = sheet
                        break

                if target_sheet:
                    df = pd.read_excel(file_path, sheet_name=target_sheet, engine='openpyxl')
                else:
                    df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
            except Exception as e:
                logging.error(f"❌ 解析Excel失败 (请检查是否安装openpyxl): {e}")
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