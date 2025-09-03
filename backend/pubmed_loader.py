"""Load documents from PubMed."""
from Bio import Entrez
from typing import List
from langchain.schema import Document
#MY_WAY - 将pubmed所需的email从环境变量中读取
import os
from dotenv import load_dotenv
import time
#
def load_pubmed_docs(
        query: str,
        max_results: int = 1000, 
        email: str = None,
        page_size: int = 100,
        fetch_batch_size: int = 200
        ) -> List[Document]:
    """
    从 PubMed 加载文档
    
    Args:
        query: PubMed 搜索查询
        max_results: 最大结果数量
        email: 您的邮箱地址（NCBI 要求）
    
    Returns:
        List[Document]: 包含 PubMed 文章的文档列表
    """
    #MY_WAY - 没有填邮箱就是我的默认邮箱
    if email is None:
        load_dotenv(os.path.join(os.path.dirname(__file__), '.env')) #NOTE -  os.path.dirname(__file__)为当前目录
        email = os.environ.get("PUBMED_EMAIL")
    if not email:
        raise ValueError("必须提供邮箱地址以便访问 PubMed API")
        
    Entrez.email = email
    #MY_WAY -1.Esearch分页收集PMID
    all_ids: List[str] = []
    retstar = 0
    while len(all_id) < max_results:
        retmax = min(page_size,max_results - len(all_ids))
        handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax, retstar=retstar)
        search = Entrez.read(handle)
        handle.close()

        ids = search.get("IdList", [])
        if not ids:
            break
        all_ids.extend(ids)
        # 若本页返回不足retmax，说明已经到末尾
        if len(ids) < retmax:
            break
        retstart += retstar
        time.sleep(0.34)
    # 搜索 PubMed
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    
    # 获取文章详情
    id_list = record["IdList"]
    handle = Entrez.efetch(db="pubmed", id=id_list, rettype="medline", retmode="xml")
    records = Entrez.read(handle)
    handle.close()
    
    documents = []
    for record in records["PubmedArticle"]:
        article = record["MedlineCitation"]["Article"]
        pmid = record["MedlineCitation"]["PMID"]
        
        # 提取文章信息
        title = article.get("ArticleTitle", "")
        abstract = article.get("Abstract", {}).get("AbstractText", [""])[0]
        authors = [
            author["LastName"] + " " + author.get("ForeName", "")
            for author in article.get("AuthorList", [])
        ] if "AuthorList" in article else []
        
        # 创建文档
        doc = Document(
            page_content=f"{title}\n\n{abstract}",
            metadata={
                "source": f"pubmed_{pmid}",
                "title": title,
                "authors": ", ".join(authors),
                "pmid": pmid
            }
        )
        documents.append(doc)
    
    return documents
# ...existing code...

if __name__ == "__main__":
    # 示例：测试 PubMed 查询
    docs = load_pubmed_docs(query="cancer", max_results=3)
    for doc in docs:
        print(doc.metadata)
        print(doc.page_content[:100])  # 只打印前100个字符，避免太长
        print("="*40)